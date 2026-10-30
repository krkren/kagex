@loadcell
@loop
;
@macro name=copyone
@copy dx=0 dy=0 sx=%x sy=0 sw=43 sh=43
@wait time=50
@endmacro
;
*start
@copyone x=0
@copyone x=43
@copyone x=86
@copyone x=129
@copyone x=172
@copyone x=215
@copyone x=258
@copyone x=301
@copyone x=344
@copyone x=387
@copyone x=430
@copyone x=473
@copyone x=516
@copyone x=559
@copyone x=602
;
@copyone x=645
;
@copyone x=602
@copyone x=559
@copyone x=516
@copyone x=473
@copyone x=430
@copyone x=387
@copyone x=344
@copyone x=301
@copyone x=258
@copyone x=215
@copyone x=172
@copyone x=129
@copyone x=86
@copyone x=43
@jump target=*start
