# Melody-lyric alignment data
All source URLs of the 1,000 songs for creating melody-lyric alignment data [[1]](#1)

In progress (512 songs / 1,000 songs)


## Description
We provide scripts for melody-lyric alignment.

## Requirement
`Python2`  
`pip install romkan`  
`pip install jaconv`  
`pip install jcconv`  
 
  install [stanford corenlp pywrapper](https://github.com/brendano/stanford_corenlp_pywrapper)  

Japanese Morpheme Parser `Mecab` [url](https://taku910.github.io/mecab/)
Japanese Dependency Parser `CaboCha` [url](https://taku910.github.io/cabocha/)
python module for `MeCab` and `CaboCha`  
`MeCab` Dictionary `ipadic` and `UniDic`

`nkf` (character code converter (Shift-JIS -> UTF8))


## Usage
### 0a. Change default encoding
Change directory python site-packages (e.g. ~/anaconda2/envs/py2/lib/python2.3/site-packages/).
Edit `sitecustomize.py`
```
import sys
sys.setdefaultencoding("utf-8")
```

### 0b. Prepare dictionary files
```shell
wget http://nlp.stanford.edu/software/stanford-corenlp-full-2013-06-20.zip 
unzip stanford-corenlp-full-2013-06-20.zip
```
Download `ipadic` and `unidic` from [MeCab: Yet Another Part-of-Speech and Morphological Analyzer](http://taku910.github.io/mecab/) and [UniDic](http://unidic.ninjal.ac.jp/download).  
```shell
mv unidic dic/
mv dic/dicrc dic/unidic/
mv ipadic dic/
```

### 1. Collect text and melody files
1. Prepare `lyrics.txt` of the following format.
```
@title sample
@artist anonymous
これはサンプルです
歌詞は行と段落で構成されます

段落の間には1行の空行があります

英語が混ざっている日本語の曲も対応しています
```

2. Prepare `melody.ust` of the following format.
(See [Utau - Wikipedia](https://en.wikipedia.org/wiki/Utau))


3. Convert character code of UTAU file. (Shift-JIS -> UTF8)
```shell
nkf -w8 --overwrite melody.ust
```


### 2. Move text and melody files
```shell
mkdir pair_data   
mkdir pair_data/sample  
cp lyrics.txt pair_data/sample/sample.txt
cp melody.ust pair_data/sample/sample.ust
```

### 3. Run!
* Text format 
`python align_data_readable.py > data.txt`

* JSON format 
`python align_data_json.py > data.jsonl`

## Data format
See sample `data.txt` or `data.jsonl`


---

- <i id=1></i>[1] Kento Watanabe, Yuichiroh Matsubayashi, Satoru Fukayama, Masataka Goto, Kentaro Inui and Tomoyasu Nakano. A Melody-conditioned Lyrics Language Model. 
    In Proceedings of the 16th Annual Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT 2018)
