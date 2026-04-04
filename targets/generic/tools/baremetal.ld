ENTRY(_start)
MEMORY {
    RAM (rx) : ORIGIN = 0x00080000, LENGTH = 256M
}
SECTIONS {
    . = 0x00080000;
    .text : {
        *(.text.startup)
        *(.text)
    }
    .rodata : {
        *(.rodata*)
    }
    .data : {
        *(.data*)
    }
    .bss : {
        *(.bss*)
        *(COMMON)
    }
    /DISCARD/ : {
        *(.comment)
        *(.note.GNU-stack)
        *(.note*)
    }
}
