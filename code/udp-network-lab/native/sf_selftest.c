/* 차등 검증 — Python 레퍼런스가 만든 (기대사유, hex) 벡터를 C 로 복호해 대조. */
#include "secure_framing.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static const uint8_t KEY[] = "grippers-preshared-key-2026";

static int nib(char c){ return c<='9' ? c-'0' : (c|32)-'a'+10; }

int main(int argc, char**argv){
    FILE*f = fopen(argc>1?argv[1]:"vectors.txt","r");
    if(!f){ perror("vectors"); return 2; }
    char reason[32], hex[16384]; int total=0, ok=0;
    while(fscanf(f,"%31s %16383s", reason, hex)==2){
        size_t n = strlen(hex)/2; uint8_t*buf = malloc(n?n:1);
        for(size_t i=0;i<n;i++) buf[i] = (uint8_t)(nib(hex[2*i])*16 + nib(hex[2*i+1]));
        sf_decoded out; sf_reason r = sf_decode(buf, n, KEY, sizeof(KEY)-1, &out);
        const char*got = sf_reason_name(r);
        int match = strcmp(got, reason)==0; total++; ok+=match;
        printf("  [%s] 기대=%-11s C=%-11s\n", match?"PASS":"FAIL", reason, got);
        free(buf);
    }
    fclose(f);
    printf("\n%d/%d 차등 일치\n", ok, total);
    return ok==total ? 0 : 1;
}
