# VSL Agencias de Viajes — con gráficos animados (1080p)

El vídeo está dividido en 4 partes (GitHub no admite archivos de más de 100 MB).

| Parte | Tramo |
|---|---|
| VSL_1080p_parte1_de_4.mp4 | 0:00 – 1:16 |
| VSL_1080p_parte2_de_4.mp4 | 1:16 – 2:25 |
| VSL_1080p_parte3_de_4.mp4 | 2:25 – 3:31 |
| VSL_1080p_parte4_de_4.mp4 | 3:31 – 4:34 |

Para unirlas sin perder calidad:

```
printf "file 'VSL_1080p_parte%d_de_4.mp4'\n" 1 2 3 4 > lista.txt
ffmpeg -f concat -safe 0 -i lista.txt -c copy VSL_Agencias_de_Viajes_1080p.mp4
```

O impórtalas en orden en cualquier editor de vídeo (CapCut, iMovie, Premiere…).
