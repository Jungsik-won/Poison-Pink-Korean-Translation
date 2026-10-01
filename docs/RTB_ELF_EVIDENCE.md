# RTB loader evidence from SLPS_258.54

Correct LOAD conversion: file offset = VA - 0x000ff000.

## compact unsigned count

```text
003ac930: d0ffbd27 addiu $sp, $sp, -0x30
003ac934: 1000b0ff sd $s0, 0x10($sp)
003ac938: 1800b1ff sd $s1, 0x18($sp)
003ac93c: 2000bfff sd $ra, 0x20($sp)
003ac940: 2d80a000 move $s0, $a1
003ac944: 2d888000 move $s1, $a0
003ac948: b8fb0d0c jal 0x37eee0
003ac94c: 2d28a003 move $a1, $sp
003ac950: 0000ae93 lbu $t6, ($sp)
003ac954: 2d202002 move $a0, $s1
003ac958: ff000f24 addiu $t7, $zero, 0xff
003ac95c: 0a00cf15 bne $t6, $t7, 0x3ac988
003ac960: 0400a527 addiu $a1, $sp, 4
003ac964: dcfb0d0c jal 0x37ef70
003ac968: 00000000 nop 
003ac96c: 0400af8f lw $t7, 4($sp)
003ac970: 00000fae sw $t7, ($s0)
003ac974: 1000b0df ld $s0, 0x10($sp)
003ac978: 1800b1df ld $s1, 0x18($sp)
003ac97c: 2000bfdf ld $ra, 0x20($sp)
003ac980: 0800e003 jr $ra
003ac984: 3000bd27 addiu $sp, $sp, 0x30
003ac988: fe000f24 addiu $t7, $zero, 0xfe
003ac98c: f9ffcf55 bnel $t6, $t7, 0x3ac974
003ac990: 00000eae sw $t6, ($s0)
003ac994: 2d202002 move $a0, $s1
003ac998: b2fb0d0c jal 0x37eec8
003ac99c: 0200a527 addiu $a1, $sp, 2
003ac9a0: f3ff0010 b 0x3ac970
003ac9a4: 0200af97 lhu $t7, 2($sp)
```

## module section order

```text
0022ba4c: 2d206002 move $a0, $s3
0022ba50: 2d28a002 move $a1, $s5
0022ba54: 2d304002 move $a2, $s2
0022ba58: e4a1080c jal 0x228790
0022ba5c: 01001424 addiu $s4, $zero, 1
0022ba60: 20006426 addiu $a0, $s3, 0x20
0022ba64: 2d28a002 move $a1, $s5
0022ba68: baa2080c jal 0x228ae8
0022ba6c: 2d304002 move $a2, $s2
0022ba70: eec1080c jal 0x2307b8
0022ba74: 38000424 addiu $a0, $zero, 0x38
0022ba78: 4f000f3c lui $t7, 0x4f
0022ba7c: 040040ac sw $zero, 4($v0)
0022ba80: a833ef25 addiu $t7, $t7, 0x33a8
0022ba84: 080040ac sw $zero, 8($v0)
0022ba88: 00004fac sw $t7, ($v0)
0022ba8c: 2d804000 move $s0, $v0
0022ba90: a4b8080c jal 0x22e290
0022ba94: 0c004424 addiu $a0, $v0, 0xc
0022ba98: fc0070ae sw $s0, 0xfc($s3)
0022ba9c: 2d28a002 move $a1, $s5
0022baa0: 2da00000 move $s4, $zero
0022baa4: 2d200002 move $a0, $s0
0022baa8: 8079080c jal 0x21e600
0022baac: 2d304002 move $a2, $s2
```

## function loader

```text
0021e600: e0ffbd27 addiu $sp, $sp, -0x20
0021e604: 1000b2ff sd $s2, 0x10($sp)
0021e608: 0000b0ff sd $s0, ($sp)
0021e60c: 0800b1ff sd $s1, 8($sp)
0021e610: 2d90a000 move $s2, $a1
0021e614: 08008524 addiu $a1, $a0, 8
0021e618: 1800bfff sd $ra, 0x18($sp)
0021e61c: 2d808000 move $s0, $a0
0021e620: 2d88c000 move $s1, $a2
0021e624: 2d20c000 move $a0, $a2
0021e628: 14b30e0c jal 0x3acc50
0021e62c: 0c001026 addiu $s0, $s0, 0xc
0021e630: 2d200002 move $a0, $s0
0021e634: 2d284002 move $a1, $s2
0021e638: 5ab9080c jal 0x22e568
0021e63c: 2d302002 move $a2, $s1
```

## function metadata and instruction array

```text
0022e68c: 10008526 addiu $a1, $s4, 0x10
0022e690: 4cb20e0c jal 0x3ac930
0022e694: 2d20a002 move $a0, $s5
0022e698: 14008526 addiu $a1, $s4, 0x14
0022e69c: 4cb20e0c jal 0x3ac930
0022e6a0: 2d20a002 move $a0, $s5
0022e6a4: 2d20a002 move $a0, $s5
0022e6a8: 4cb20e0c jal 0x3ac930
0022e6ac: 7000a527 addiu $a1, $sp, 0x70
0022e6b0: 2d20a002 move $a0, $s5
0022e6b4: 4cb20e0c jal 0x3ac930
0022e6b8: 7400a527 addiu $a1, $sp, 0x74
0022e6bc: 0c008f8e lw $t7, 0xc($s4)
0022e6c0: 0400938e lw $s3, 4($s4)
0022e6c4: 7000b28f lw $s2, 0x70($sp)
0022e6c8: 2378f301 subu $t7, $t7, $s3
0022e6cc: 83780f00 sra $t7, $t7, 2
0022e6d0: 2b78f201 sltu $t7, $t7, $s2
0022e6d4: 1800e011 beqz $t7, 0x22e738
0022e6d8: 80901200 sll $s2, $s2, 2
0022e6dc: 0800908e lw $s0, 8($s4)
0022e6e0: d4fb0c0c jal 0x33ef50
0022e6e4: 2d204002 move $a0, $s2
0022e6e8: 23801302 subu $s0, $s0, $s3
0022e6ec: 2d884000 move $s1, $v0
0022e6f0: 2d300002 move $a2, $s0
0022e6f4: 2d204000 move $a0, $v0
0022e6f8: 475b0d0c jal 0x356d1c
0022e6fc: 2d286002 move $a1, $s3
0022e700: 83801000 sra $s0, $s0, 2
0022e704: 04008f8e lw $t7, 4($s4)
0022e708: 2d208002 move $a0, $s4
0022e70c: 0c00868e lw $a2, 0xc($s4)
0022e710: 80801000 sll $s0, $s0, 2
0022e714: 2d28e001 move $a1, $t7
0022e718: 21903202 addu $s2, $s1, $s2
0022e71c: 2330cf00 subu $a2, $a2, $t7
0022e720: 21803002 addu $s0, $s1, $s0
0022e724: e4d10e0c jal 0x3b4790
0022e728: 83300600 sra $a2, $a2, 2
0022e72c: 0c0092ae sw $s2, 0xc($s4)
0022e730: 080090ae sw $s0, 8($s4)
0022e734: 040091ae sw $s1, 4($s4)
0022e738: 7400a48f lw $a0, 0x74($sp)
0022e73c: d4fb0c0c jal 0x33ef50
0022e740: 6000b127 addiu $s1, $sp, 0x60
0022e744: 280082ae sw $v0, 0x28($s4)
0022e748: 2d804000 move $s0, $v0
0022e74c: 2d282002 move $a1, $s1
0022e750: b8fb0d0c jal 0x37eee0
0022e754: 2d20a002 move $a0, $s5
0022e758: 6000a593 lbu $a1, 0x60($sp)
0022e75c: b901a010 beqz $a1, 0x22ee44
0022e760: d7ffae24 addiu $t6, $a1, -0x29
0022e764: 4700cf2d sltiu $t7, $t6, 0x47
0022e768: b101e011 beqz $t7, 0x22ee30
0022e76c: 80780e00 sll $t7, $t6, 2
0022e770: 53000e3c lui $t6, 0x53
0022e774: e0aace25 addiu $t6, $t6, -0x5520
0022e778: 2178ee01 addu $t7, $t7, $t6
0022e77c: 0000ed8d lw $t5, ($t7)
0022e780: 0800a001 jr $t5
0022e784: 00000000 nop 
```

## one pointer per instruction and reader dispatch

```text
0022e7b8: 7800b0af sw $s0, 0x78($sp)
0022e7bc: 0800858e lw $a1, 8($s4)
0022e7c0: 0c008f8e lw $t7, 0xc($s4)
0022e7c4: 1300af10 beq $a1, $t7, 0x22e814
0022e7c8: 7800a627 addiu $a2, $sp, 0x78
0022e7cc: 0100a054 bnel $a1, $zero, 0x22e7d4
0022e7d0: 0000b0ac sw $s0, ($a1)
0022e7d4: 0400af24 addiu $t7, $a1, 4
0022e7d8: 08008fae sw $t7, 8($s4)
0022e7dc: 7800a48f lw $a0, 0x78($sp)
0022e7e0: 00008f8c lw $t7, ($a0)
0022e7e4: 1400e28d lw $v0, 0x14($t7)
0022e7e8: 09f84000 jalr $v0
0022e7ec: 00000000 nop 
0022e7f0: 21800202 addu $s0, $s0, $v0
0022e7f4: 7800a48f lw $a0, 0x78($sp)
0022e7f8: 2d28e002 move $a1, $s7
0022e7fc: 00008e8c lw $t6, ($a0)
0022e800: 0c00cf8d lw $t7, 0xc($t6)
0022e804: 09f8e001 jalr $t7
0022e808: 2d30a002 move $a2, $s5
0022e80c: d0ff0010 b 0x22e750
0022e810: 2d282002 move $a1, $s1
```

## string length and content reader

```text
00236cf0: 90febd27 addiu $sp, $sp, -0x170
00236cf4: 04008524 addiu $a1, $a0, 4
00236cf8: 5001b2ff sd $s2, 0x150($sp)
00236cfc: 4001b0ff sd $s0, 0x140($sp)
00236d00: 4801b1ff sd $s1, 0x148($sp)
00236d04: 2d908000 move $s2, $a0
00236d08: 5801b3ff sd $s3, 0x158($sp)
00236d0c: 2d80c000 move $s0, $a2
00236d10: 6001bfff sd $ra, 0x160($sp)
00236d14: dcfb0d0c jal 0x37ef70
00236d18: 2d20c000 move $a0, $a2
00236d1c: 65000d3c lui $t5, 0x65
00236d20: 2000a527 addiu $a1, $sp, 0x20
00236d24: 90ebad25 addiu $t5, $t5, -0x1470
00236d28: 2d200002 move $a0, $s0
00236d2c: 0800ae8d lw $t6, 8($t5)
00236d30: 0c00af25 addiu $t7, $t5, 0xc
00236d34: 0000afaf sw $t7, ($sp)
00236d38: 0100ce25 addiu $t6, $t6, 1
00236d3c: b8fb0d0c jal 0x37eee0
00236d40: 0800aead sw $t6, 8($t5)
00236d44: 2000a693 lbu $a2, 0x20($sp)
00236d48: 2600c010 beqz $a2, 0x236de4
00236d4c: 3000b127 addiu $s1, $sp, 0x30
00236d50: 2d200002 move $a0, $s0
00236d54: 1ab50e0c jal 0x3ad468
00236d58: 2d282002 move $a1, $s1
00236d5c: 55000e3c lui $t6, 0x55
```

## jump execution

```text
00236890: 08008e8c lw $t6, 8($a0)
00236894: 2d100000 move $v0, $zero
00236898: 1000cf8c lw $t7, 0x10($a2)
0023689c: 80700e00 sll $t6, $t6, 2
002368a0: 2178ee01 addu $t7, $t7, $t6
002368a4: 0800e003 jr $ra
002368a8: 1000cfac sw $t7, 0x10($a2)
```

## conditional branch and fallthrough

```text
0023693c: 0e006056 bnel $s3, $zero, 0x236978
00236940: 10000f8e lw $t7, 0x10($s0)
00236944: 08004f8e lw $t7, 8($s2)
00236948: 10000e8e lw $t6, 0x10($s0)
0023694c: 80780f00 sll $t7, $t7, 2
00236950: 2170cf01 addu $t6, $t6, $t7
00236954: 10000eae sw $t6, 0x10($s0)
00236958: 1000b0df ld $s0, 0x10($sp)
0023695c: 2d100000 move $v0, $zero
00236960: 1800b1df ld $s1, 0x18($sp)
00236964: 2000b2df ld $s2, 0x20($sp)
00236968: 2800b3df ld $s3, 0x28($sp)
0023696c: 3000bfdf ld $ra, 0x30($sp)
00236970: 0800e003 jr $ra
00236974: 4000bd27 addiu $sp, $sp, 0x40
00236978: 0400ef25 addiu $t7, $t7, 4
0023697c: f6ff0010 b 0x236958
00236980: 10000fae sw $t7, 0x10($s0)
```

## jump operand reader

```text
00237418: e0ffbd27 addiu $sp, $sp, -0x20
0023741c: 04008524 addiu $a1, $a0, 4
00237420: 0000b0ff sd $s0, ($sp)
00237424: 0800b1ff sd $s1, 8($sp)
00237428: 1000bfff sd $ra, 0x10($sp)
0023742c: 2d808000 move $s0, $a0
00237430: 2d88c000 move $s1, $a2
00237434: dcfb0d0c jal 0x37ef70
00237438: 2d20c000 move $a0, $a2
0023743c: 08001026 addiu $s0, $s0, 8
00237440: 2d202002 move $a0, $s1
00237444: 1000bfdf ld $ra, 0x10($sp)
00237448: 2d280002 move $a1, $s0
0023744c: 0800b1df ld $s1, 8($sp)
00237450: 0000b0df ld $s0, ($sp)
00237454: 5ac00e08 j 0x3b0168
00237458: 2000bd27 addiu $sp, $sp, 0x20
```
