for file in *.tar.gz; do
    paper_id=${file%.*.*}
    #mkdir $paper_id
    #tar zxf $file -C ./$paper_id
    tar zxf $file
    #rm $file
    cd $paper_id  
    echo '------------'$paper_id'------------'
    mains=$(grep -l "begin{document}" *.tex)
    for main in $mains; do
        python ~/github/latexMacroParser/demacro.py $main ../$paper_id'.tex'
    done
    cd ..
done