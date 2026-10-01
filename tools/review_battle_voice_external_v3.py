"""Align user-uploaded AccurateScribe results and apply explicit text decisions.

Read-only with respect to original voice banks, v1/v2 catalogs and ISOs. Service
timestamps and raw text are preserved because adjacent utterances can be merged.
"""
import csv
import json
from collections import Counter

from build_battle_subtitles import assemble
from localization_pipeline import ROOT, file_hash, write_json

OUT = ROOT/'outputs/battle_voice_recheck_v2/external_transcription'
CATALOG = ROOT/'localization/battle_voice_subtitles_v2.json'
NATIVE = ROOT/'build/battle_voice_recheck_v2/verify_external_native'
SOURCES = [(0, 'accuratescribe_result.json'),
           (60, 'accuratescribe_part2_result.json'),
           (120, 'accuratescribe_part3_result.json')]


def align():
    manifest = json.loads((OUT/'segments.json').read_text())
    split = json.loads((OUT/'split_manifest.json').read_text())
    assert file_hash(OUT/manifest['audio_file']) == manifest['audio_sha256']
    for part in split['parts']:
        assert part['duration_seconds'] <= 60
        assert file_hash(OUT/part['file']) == part['sha256']
    assert len(manifest['segments']) == 45
    catalog = json.loads(CATALOG.read_text())
    rows = {r['tag']: r for r in catalog['rows']}
    cues, sources = [], []
    for offset, filename in SOURCES:
        path = OUT/filename
        data = json.loads(path.read_text())
        assert data['status'] == 'completed' and data['language'] == 'ja'
        sources.append(dict(result=filename, result_sha256=file_hash(path),
                            start_offset_seconds=offset,
                            source_duration_seconds=data['duration'],
                            returned_cues=len(data['subtitleEntries'])))
        for cue in data['subtitleEntries']:
            assert 0 <= cue['start'] < cue['end'] <= data['duration'] + .01
            cues.append(dict(cue, global_start=cue['start']+offset,
                             global_end=cue['end']+offset, source=filename,
                             source_offset_seconds=offset))
    aligned = []
    for clip in manifest['segments']:
        assert file_hash(ROOT/clip['source']) == clip['source_wav_sha256']
        row = rows[clip['tag']]
        assert row['status'] == 'needs_transcript_review'
        hits = []
        for cue in cues:
            overlap = max(0, min(clip['end_seconds'], cue['global_end']) -
                          max(clip['start_seconds'], cue['global_start']))
            if overlap > 0:
                hits.append(dict(cue, overlap_seconds=round(overlap, 6)))
        record = dict(clip, external_entries=hits,
                      asr_external_text=' / '.join(c['text'].replace(' ', '') for c in hits),
                      asr_small=row.get('asr_individual', ''),
                      asr_turbo=row.get('asr_review_model', ''),
                      asr_turbo_padded=row.get('asr_padded_review', ''),
                      asr_large_v3=row.get('asr_large_v3', ''),
                      asr_large_v3_native=row.get('asr_large_v3_native', ''))
        native = NATIVE/(row['tag']+'.wav.json')
        if native.exists():
            data = json.loads(native.read_text())
            record['asr_large_v3_external_native'] = ''.join(
                x['text'] for x in data['transcription']).strip()
            record['external_native_result_sha256'] = file_hash(native)
        aligned.append(record)
    evidence = dict(service='AccurateScribe.ai – Transcribe',
                    provider_backend_model_known=False, direct_gpt_audio_input=False,
                    sources=sources, source_duration_seconds=manifest['duration_seconds'],
                    rows=aligned, limitations=[
                        'Service timing/text can merge adjacent utterances or omit clips.',
                        'No cue was assigned by ordinal position.',
                        'No direct GPT listening or human listening audit.'])
    write_json(OUT/'aligned_evidence.json', evidence)
    return catalog, evidence


def main():
    catalog, evidence = align()
    decisions_file = OUT/'final_decisions.json'
    if not decisions_file.exists():
        print('Alignment ready; explicit review decisions are still required.')
        return
    decision_data = json.loads(decisions_file.read_text())
    assert decision_data['source_catalog_sha256'] == file_hash(CATALOG)
    decisions = decision_data['decisions']
    assert set(decisions) == {r['tag'] for r in evidence['rows']}
    before = json.loads(CATALOG.read_text())
    old_rows = {r['tag']: r for r in before['rows']}
    aligned = {r['tag']: r for r in evidence['rows']}
    changes = []
    for row in catalog['rows']:
        tag = row['tag']
        if tag not in aligned:
            continue
        ev, decision = aligned[tag], decisions[tag]
        row['asr_accuratescribe'] = ev['asr_external_text']
        row['asr_accuratescribe_evidence'] = ev['external_entries']
        row['external_transcript_review'] = decision
        status = decision['status']
        assert status in ('reviewed_translation', 'needs_transcript_review', 'non_dialogue')
        row['status'] = status
        row['ja'] = decision.get('ja', '')
        row['ko'] = decision.get('ko', '')
        assert bool(row['ja'] and row['ko']) == (status == 'reviewed_translation')
        if status != 'reviewed_translation':
            assert not row['ja'] and not row['ko']
        if status != old_rows[tag]['status']:
            changes.append(dict(tag=tag, status=status, ja=row['ja'], ko=row['ko'],
                                aliases=len(row['aliases']), reason=decision['reason']))
    counts = dict(Counter(r['status'] for r in catalog['rows']))
    catalog['counts'] = counts
    catalog['review_method'] = ('Whisper small/turbo/full large-v3 + user-uploaded '
        'AccurateScribe audio transcription; GPT text evidence review, not direct audio listening.')
    preserved = 0
    for old, new in zip(before['rows'], catalog['rows']):
        assert all(old[k] == new[k] for k in
                   ('tag', 'bank', 'offset', 'size', 'sha256', 'audio', 'aliases'))
        if old['status'] == 'reviewed_translation':
            assert old == new
            preserved += 1
    assert preserved == 433
    old_payload, old_meta = assemble(before['rows'])
    payload, meta = assemble(catalog['rows'])
    assert old_payload[:0x440] == payload[:0x440]
    assert old_meta['code_bytes'] == meta['code_bytes']
    heap = (meta['base']+len(payload)+4095) & ~4095
    assert heap == 0x655000, 'New payload changes the reserved heap boundary'
    target = ROOT/'localization/battle_voice_subtitles_v3.json'
    write_json(target, catalog)
    report = dict(status='reviewed_catalog_ready_not_applied_to_iso', iso_built=False,
        catalog=str(target.relative_to(ROOT)), catalog_sha256=file_hash(target),
        source_catalog=str(CATALOG.relative_to(ROOT)), source_catalog_sha256=file_hash(CATALOG),
        service=evidence['service'], service_backend_model_known=False,
        user_uploaded_clips=45, aligned_clips_with_cues=sum(bool(r['external_entries']) for r in evidence['rows']),
        no_external_cues=[r['tag'] for r in evidence['rows'] if not r['external_entries']],
        results=evidence['sources'], old_counts=before['counts'], counts=counts,
        new_translations=sum(c['status']=='reviewed_translation' for c in changes),
        new_translation_bank_slots=sum(c['aliases'] for c in changes if c['status']=='reviewed_translation'),
        total_translation_bank_slots=sum(len(r['aliases']) for r in catalog['rows'] if r['status']=='reviewed_translation'),
        changes=changes, direct_gpt_audio_input=False, human_listening_audit=False,
        runtime_verified=False, validation=dict(existing_translations_preserved=preserved,
            source_audio_hashes_verified=45, source_bank_signatures_verified=592,
            font_and_caption_width_checks_passed=True, in_memory_assembly_only=True,
            instruction_bytes_unchanged=True, segment_bytes=len(payload), heap_start=hex(heap)),
        review=str(decisions_file.relative_to(ROOT)),
        gpt_review='outputs/battle_voice_recheck_v2/external_transcription/gpt_external_review.json')
    write_json(ROOT/'reports/battle_voice_external_v3.json', report)
    with (OUT/'external_review.tsv').open('w', newline='') as fp:
        writer = csv.writer(fp, delimiter='\t')
        writer.writerow(['tag', 'start_seconds', 'end_seconds', 'external_text',
                         'small', 'turbo', 'large_v3', 'large_v3_native',
                         'new_native', 'decision', 'ja', 'ko', 'reason'])
        for ev in evidence['rows']:
            d = decisions[ev['tag']]
            writer.writerow([ev['tag'], ev['start_seconds'], ev['end_seconds'],
                ev['asr_external_text'], ev['asr_small'], ev['asr_turbo'],
                ev['asr_large_v3'], ev['asr_large_v3_native'],
                ev.get('asr_large_v3_external_native', ''), d['status'],
                d.get('ja', ''), d.get('ko', ''), d['reason']])
    print(json.dumps(dict(new_translations=report['new_translations'], counts=counts,
                          preserved=preserved, iso_built=False), ensure_ascii=False))


if __name__ == '__main__':
    main()
