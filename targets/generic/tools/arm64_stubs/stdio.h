
#ifndef _STDIO_H
#define _STDIO_H
typedef unsigned long size_t;
typedef struct { char _data[64]; } FILE;
extern FILE __stdin_FILE;
extern FILE __stdout_FILE;
extern FILE __stderr_FILE;
#define stdin  (&__stdin_FILE)
#define stdout (&__stdout_FILE)
#define stderr (&__stderr_FILE)
#define NULL   ((void*)0)
#define EOF    (-1)
int printf(const char *fmt, ...);
int sprintf(char *buf, const char *fmt, ...);
int snprintf(char *buf, size_t n, const char *fmt, ...);
int fprintf(FILE *f, const char *fmt, ...);
int puts(const char *s);
int fflush(FILE *f);
void exit(int code) __attribute__((noreturn));
#endif
