# -*- coding: utf-8 -*-
# For python2
import sys
import glob
import json
import argparse
import alignment
from collections import defaultdict

import logging
logging.disable(logging.FATAL)

import romkan
import jaconv
from jcconv import *

from stanford_corenlp_pywrapper import CoreNLP          # git clone https://github.com/brendano/stanford_corenlp_pywrapper
corenlp_dir = "./stanford-corenlp-full-2013-06-20/"     # wget http://nlp.stanford.edu/software/stanford-corenlp-full-2013-06-20.zip
proc = CoreNLP(configdict={'annotators': 'tokenize,ssplit,pos,lemma'},  corenlp_jars=["./stanford-corenlp-full-2013-06-20/*"])

import re
en_p = re.compile(ur"[a-zA-Z\']")
num_p = re.compile(ur"[0-9\']")
hira_p = re.compile(u"[ぁ-ん]")
kata_p = re.compile(u"[ァ-ン]")
re_katakana = re.compile(ur'^(?:[\u30A1-\u30F4|ー|_])+$')

import MeCab
import CaboCha
cabocha_tagger = CaboCha.Parser("-f1 -d ./dic/ipadic")
accent_tagger = MeCab.Tagger("-d ./dic/unidic")

en2kana = {}
for strm in open("./dic/en2kana.txt", "r"):
    en = strm.strip().split("\t")[0]
    kana = strm.strip().split("\t")[1]
    en2kana[en] = kana


"""
lyrics parsing functions
"""
def parse(text):
    phrase = []
    words = []
    for morph in cabocha_tagger.parseToString(text.encode("utf8")).split("\n"):
        if morph.strip() == "" or morph.strip() == "EOS": continue
        if morph.strip().split(" ")[0] == "*":
            if phrase:
                phrase_lyrics = get_phrase(phrase, phrase_info)
                phrase = []
                for word in phrase_lyrics['word']:
                    accent = []
                    for syllable in word['syllable']:
                        accent.append(syllable['accent'])
                    yomi = "_".join(get_yomi(word['info'].split(',')[-1]))
                    if yomi == "*" and re_katakana.search(unicode(word['sur'])):
                        yomi = "_".join(get_yomi(word['sur']))
                    words.append("%s,%s,%s"%(','.join(word['info'].split(',')[:-1:]), yomi, '_'.join(accent)))
            phrase_info = morph.split(" ")[1::]
        else:
            phrase.append(morph)
    phrase_lyrics = get_phrase(phrase, phrase_info)
    for word in phrase_lyrics['word']:
        accent = []
        for syllable in word['syllable']:
            accent.append(syllable['accent'])
        yomi = "_".join(get_yomi(word['info'].split(',')[-1]))
        if yomi == "*" and re_katakana.search(unicode(word['sur'])):
            yomi = "_".join(get_yomi(word['sur']))
        words.append("%s,%s,%s"%(','.join(word['info'].split(',')[:-1:]), yomi, '_'.join(accent)))
    return words

def get_phrase(phrase, phrase_info):
    phrase_lyrics = {"sur": " ".join([w.split("\t")[0] for w in phrase]), 
            "info": " ".join(phrase_info), 
            "word":[]}
    accent = get_accent("".join([w.split("\t")[0] for w in phrase]))
    mora = 0
    acc_idx = 0
    for word in phrase:
        sur = word.split("\t")[0]
        if en_p.match(unicode(sur)):
            word = parse_eng_word(sur)
        kana = word.split("\t")[1].split(",")[-1]
        kana = "".join(get_yomi(kana))
        if kana == "*":
            kana = sur
        mora += get_mora(kana)
        kana = "q".join(kana.split("ッ"))
        kana = "".join(kana.split("ー"))
        kana = "N".join(kana.split("ン"))
        word_alpha = split_alpha(kana)
        word_lyrics = {"sur":sur, "kana":kana, "info":word, "syllable":[]}
        for w_a in word_alpha:
            syllable_lyrics = {}
            out_char = [w_a[0], w_a[1]]
            if out_char[1] == "*":
                #print "\t" + "\t".join(out_char) + "\t" + "*" 
                syllable_lyrics["sur"] = w_a[0]
                syllable_lyrics["roma"] = w_a[1]
                syllable_lyrics["accent"] = "*"
            else:
                if len(accent) <= mora:      
                    #print "\t" + "\t".join(out_char) + "\t" + accent[-1] 
                    syllable_lyrics["sur"] = w_a[0]
                    syllable_lyrics["roma"] = w_a[1]
                    syllable_lyrics["accent"] = accent[-1]
                else:
                    #print "\t" + "\t".join(out_char) + "\t" + accent[acc_idx] 
                    syllable_lyrics["sur"] = w_a[0]
                    syllable_lyrics["roma"] = w_a[1]
                    syllable_lyrics["accent"] = accent[acc_idx]
                acc_idx += 1
            word_lyrics["syllable"].append(syllable_lyrics)
        phrase_lyrics["word"].append(word_lyrics)
    return phrase_lyrics

def parse_eng_word(term):
    result_json = proc.parse_doc(term.strip().encode("utf8"))
    morph = result_json["sentences"][0]
    for sur, pos, lemma in zip(morph["tokens"], morph["pos"], morph["lemmas"]):
        pos2 = "*"
        pos3 = "*"
        pos4 = "*"
        form1 = "*"
        form2 = "*"
        base = lemma
        kana = en2kana_db.get(sur.lower().encode("utf8"), sur.encode("utf8"))
        yomi = kana
        return "%s\t%s,%s,%s,%s,%s,%s,%s,%s,%s"%(sur, pos, pos2, pos3, pos4, form1, form2, base, kana, yomi)

def split_alpha(line):
    out = []
    for char in unicode(line):
        if char in ('ァ', 'ィ', 'ゥ', 'ェ', 'ォ', 'ャ', 'ュ', 'ョ'):
            if out:
                out[-1] += char
            else:
                out.append(char)
        else:
            out.append(char)
    return [("ッ".join("ン".join(kana.split("N")).split("q")), romkan.to_roma(kana)) for kana in out]

def get_mora(kana):
    mora = len(unicode(kana))
    for char in unicode(kana):
        if char in ('ァ', 'ィ', 'ゥ', 'ェ', 'ォ', 'ャ', 'ュ', 'ョ'):
            mora -= 1
    if mora < 0:
        mora = 0
    return mora

def get_yomi(kana):
    yomi = []
    for char in unicode(kana):
        char = char.encode('utf8')
        if char == 'ー':
            if len(yomi) == 0: continue
            if yomi[-1] in ('ア','カ','ガ','サ','ザ','タ','ダ','ナ','ハ','バ','パ','マ','ヤ','ラ','ワ','キャ','ギャ','シャ','ジャ','チャ','ヂャ','ニャ','ヒャ','ビャ','ピャ','ミャ','リャ','ファ','ヴァ'):
                yomi.append("ア")
            elif yomi[-1] in ('イ','キ','ギ','シ','ジ','チ','ヂ','ニ','ヒ','ビ','ピ','ミ','リ','ヰ','フィ','ヴィ','ディ','ティ', 'ウィ'):
                yomi.append("イ")
            elif yomi[-1] in ('ウ','ク','グ','ス','ズ','ツ','ヅ','ヌ','フ','ブ','プ','ム','ユ','ル','キュ','ギュ','シュ','ジュ','チュ','ヂュ','ニュ','ヒュ','ビュ','ピュ','ミュ','リュ','フュ','ヴュ', 'トゥ', 'ドゥ'):
                yomi.append("ウ")
            elif yomi[-1] in ('エ','ケ','ゲ','セ','ゼ','テ','デ','ネ','ヘ','ベ','ペ','メ','レ','フェ','ウェ','ヴェ','シェ','ジェ','チェ','ヂェ','ニェ','ヒェ','ビェ','ピェ','ミェ', 'イェ'):
                yomi.append("エ")
            elif yomi[-1] in ('オ','コ','ゴ','ソ','ゾ','ト','ド','ノ','ホ','ボ','ポ','モ','ヨ','ロ','ヲ','キョ','ギョ','ショ','ジョ','チョ','ヂョ','ニョ','ヒョ','ビョ','ピョ','ミョ','リョ','フォ','ブォ','ウォ','ヴォ'):
                yomi.append("オ")
            elif yomi[-1] == "ン":
                yomi.append("ン")
        elif char in ('ァィゥェォャュョ'):
            if len(yomi) > 0:
                yomi[-1] = yomi[-1] + char
            else:
                yomi.append(char)
        else:
            yomi.append(char)
    return yomi

""" 
For extracting Japanese accect information,  we used UniDic (http://unidic.ninjal.ac.jp/).
However, it is very difficult to analyze UniDic accent information (see https://repository.dl.itc.u-tokyo.ac.jp/?action=repository_action_common_download&item_id=3407&item_no=1&attribute_id=14&file_no=1 Chapter2).
We inplemented accent parser below accoding to this paper.
"""
def get_accent(phrase):
    accent_info = []
    out_accent = 0
    out_mora = 0
    head_f = False
    for morph in accent_tagger.parse(phrase.encode('utf-8')).split('\n'):
        if len(morph.split("\t")) <= 8:break        # アクセントの情報が無いものはもはや計算不能なので却下
        if morph == "EOS" or morph == "": continue
        mora = get_mora(morph.split("\t")[1])
        pos = morph.split("\t")[4].split("-")[0]
        if morph.split("\t")[7] == "":
            acc_position = 0        # アクセント核を持たないので平板とする(やり過ぎ?)
        else:
            acc_position = int(morph.split("\t")[7].split(",")[0])
        if morph.split("\t")[8] == "":
            acc_joint = None
        else:
            acc_joint = morph.split("\t")[8]
        # 結合規則をする前に修飾規則を適応する
        if morph.split("\t")[9] != "":
            acc_metric = morph.split("\t")[9]
            M, back_m = acc_metric.split("@")
            if M == "M1":
                acc_position = mora - int(back_m)
            if M == "M2":
                if acc_position == 0:
                    acc_position = mora - int(back_m)
            if M == "M4":
                if acc_position == 0:
                    pass
                elif acc_position == 1:
                    pass
                else:
                    acc_position = mora - int(back_m)
        else:
            acc_metric = None
        # step1: アクセント結合規則を調べる
        if acc_joint:
            # step1.0: 接頭辞アクセント結合規則
            if acc_joint[0] == "P":
                head_f = True
            else:
                if len(accent_info) == 0:       # 文節の先頭の時
                    out_accent = acc_position
                else:           # 先頭文節以降
                    prev_acc_joint = accent_info[-1][2]
                    prev_pos = accent_info[-1][4]
                    # step1.3: 接頭辞アクセント結合規則
                    if head_f == True and "名詞" in pos:
                        if prev_acc_joint == "P1":       # 一体化型
                            if acc_position == 0:
                                out_accent = 0
                            else:
                                out_accent = out_mora + acc_position
                        elif prev_acc_joint == "P2":       # 自立語結合型
                            if acc_position == 0:
                                out_accent =  out_mora + 1
                            else:
                                out_accent = out_mora + acc_position
                        elif prev_acc_joint == "P4":       # 混合型
                            if acc_position == 0:
                                out_accent =  out_mora + 1
                            else:
                                out_accent = out_mora + acc_position
                        elif prev_acc_joint == "P6":       # 平板型
                            out_accent = 0
                        head_f = False
                    # step1.1: 付属語アクセント結合規則     # 品詞%F6@1,-1,品詞%F4@1 みたいなひどい形式がある（単純にカンマでsplitしたくない）
                    elif len(acc_joint.split(",")[0].split("%")) > 1:
                        acc_joints = acc_joint.split(",")
                        for j in xrange(len(acc_joints)):
                            sub_rule = acc_joints[j]
                            if j+1 < len(acc_joints):    # 後ろを確認する
                                if len(acc_joints[j].split("%")) == 1:    # F6のようなフォーマットの時
                                    continue
                                if len(acc_joints[j+1].split("%")) == 1:    # F6のようなフォーマットの時
                                    sub_rule = acc_joints[j] + "," + acc_joints[j+1]
                            if len(sub_rule.split("%")) == 1: continue  # これは辞書フォーマットのバグのせい
                            if len(sub_rule.split("%")) == 1: continue  # これは辞書フォーマットのバグのせい
                            sub_rule_pos = sub_rule.split("%")[0]
                            sub_rule_F = sub_rule.split("%")[1]
                            if sub_rule_pos in prev_pos:
                                F = sub_rule_F.split("@")[0]
                                if F == "F1":       # 従属型(そのまま)
                                    pass
                                elif F == "F2":     # 不完全支配型
                                    joint_value = int(sub_rule_F.split("@")[1].split(",")[0][:2])
                                    if out_accent == 0:  # 0型アクセントに接続した場合は結合アクセント価を足す
                                        out_accent = out_mora +  joint_value
                                elif F == "F3":     # 融合型
                                    joint_value = int(sub_rule_F.split("@")[1].split(",")[0][:2])
                                    if out_accent != 0:  # 0型アクセント以外に接続した場合は結合アクセント価を足す
                                        out_accent = out_mora + joint_value
                                elif F == "F4":     # 支配型 とにかく結合アクセント価を足す
                                    joint_value = int(sub_rule_F.split("@")[1].split(",")[0][:2])
                                    out_accent = out_mora + joint_value
                                elif F == "F5":     # 平板型 アクセントが消失する
                                    out_accent = 0
                                elif F == "F6": 
                                    joint_value1 = int(sub_rule_F.split("@")[1].split(",")[0][:2])
                                    joint_value2 = int(sub_rule_F.split("@")[1].split(",")[1][:2])
                                    if out_accent == 0:  # 0型アクセントに接続した場合は第一結合アクセント価を足す
                                        out_accent = out_mora + joint_value1
                                    else:  # 0型アクセント以外に接続した場合は第二結合アクセント価を足す
                                        out_accent = out_mora + joint_value2
                                break
                    # step1.2: 複合名詞アクセント結合規則
                    elif acc_joint[0] == "C":
                        if acc_joint == "C1":       # 自立語結合保存型
                            out_accent = out_mora + acc_position
                        if acc_joint == "C2":       # 自立語結合生起型
                            out_accent = out_mora + 1
                        if acc_joint == "C3":       # 接辞結合標準型
                            out_accent = out_mora
                        if acc_joint == "C4":       # 接辞結合平板化型
                            out_accent = 0
                        if acc_joint == "C5":       # 従属型
                            out_accent = out_accent
                        if acc_joint == "C10":       # その他
                            out_accent = out_accent
        else:
            if len(accent_info) == 0:       # 文節の先頭の時
                out_accent = acc_position
        
        accent_info.append((mora, acc_position, acc_joint, acc_metric, pos))
        out_mora += mora
    hl = []
    if out_accent == 0: #0板
        hl.append("L")
        for i in xrange(out_mora-1):
            hl.append("H")
    elif out_accent == 1: #1型
        hl.append("H")
        for i in xrange(out_mora-1):
            hl.append("L")
    else:       # それ以外
        hl.append("L")
        for i in xrange(out_accent-1):
            hl.append("H")
        for i in xrange(out_mora-out_accent):
            hl.append("L")
    return hl

def get_long_sound(kana):
    kana = kana.encode("utf8")
    if kana in ('ア','カ','ガ','サ','ザ','タ','ダ','ナ','ハ','バ','パ','マ','ヤ','ラ','ワ','キャ','ギャ','シャ','ジャ','チャ','ヂャ','ニャ','ヒャ','ビャ','ピャ','ミャ','リャ','ファ','ヴァ'):
        return "ア"
    elif kana in ('イ','キ','ギ','シ','ジ','チ','ヂ','ニ','ヒ','ビ','ピ','ミ','リ','ヰ','フィ','ヴィ','ディ','ティ', 'ウィ'):
        return "イ"
    elif kana in ('ウ','ク','グ','ス','ズ','ツ','ヅ','ヌ','フ','ブ','プ','ム','ユ','ル','キュ','ギュ','シュ','ジュ','チュ','ヂュ','ニュ','ヒュ','ビュ','ピュ','ミュ','リュ','フュ','ヴュ', 'トゥ', 'ドゥ'):
        return "ウ"
    elif kana in ('エ','ケ','ゲ','セ','ゼ','テ','デ','ネ','ヘ','ベ','ペ','メ','レ','フェ','ウェ','ヴェ','シェ','ジェ','チェ','ヂェ','ニェ','ヒェ','ビェ','ピェ','ミェ', 'イェ'):
        return "エ"
    elif kana in ('オ','コ','ゴ','ソ','ゾ','ト','ド','ノ','ホ','ボ','ポ','モ','ヨ','ロ','ヲ','キョ','ギョ','ショ','ジョ','チョ','ヂョ','ニョ','ヒョ','ビョ','ピョ','ミョ','リョ','フォ','ブォ','ヴォ','ウォ'):
        return "オ"
    elif kana == "ン":
        return "ン"
    else:
        print kana
        exit(1)

"""
parse UST.
you need to convert original UST's character code (SHIFT-jis) to (UTF8)
"""
def open_ust(file_name):
    song = []
    instance = {}
    bpm = 0.0
    for strm in open(file_name, "r"):
        if strm.strip().startswith("["):
            if len(instance) > 0:
                if instance.get("Tempo", None):
                    bpm = float(".".join(instance["Tempo"].split(",")))
                if instance.get("Lyric", None):     
                    if len(instance["Lyric"].split(" ")) > 1:
                        instance["Lyric"] = instance["Lyric"].split(" ")[-1]
                    if "R" in instance["Lyric"] or "息" in instance["Lyric"]:
                        instance["Lyric"] = ""
                    if hira_p.search(unicode(instance["Lyric"])):
                        instance["Lyric"] = re.sub("[A-Za-z]+", "", instance["Lyric"])
                    else:
                        instance["Lyric"] = romkan.to_katakana(instance["Lyric"])
                    instance["Lyric"] = re.sub(u"[^ァ-ン]",  "",  unicode(instance["Lyric"])).encode("utf8")
                instance["Tempo"] = str(bpm)
                if "NoteNum" in instance:
                    if instance["Lyric"] == "":
                        instance["NoteNum"] = "rest"
                    song.append(instance)
            instance = {"InstanceIdx": strm.strip().lstrip("[#").rstrip("]")}
        else:
            if len(strm.strip().split("=")) < 2:
                continue
            key, value = strm.strip().split("=")
            if key == "Lyric":
                value = jaconv.hira2kata(unicode(value)).encode("utf8")
            if key in ("NoteNum", "Lyric", "Length", "Tempo"):
                instance[key] = value
    if len(instance) > 0:
        if instance.get("Tempo", None):
            bpm = float(".".join(instance["Tempo"].split(",")))
        if instance.get("Lyric", None):     
            if len(instance["Lyric"].split(" ")) > 1:
                instance["Lyric"] = instance["Lyric"].split(" ")[-1]
            if "R" in instance["Lyric"] or "息" in instance["Lyric"]:
                instance["Lyric"] = ""
            if hira_p.search(unicode(instance["Lyric"])):
                instance["Lyric"] = re.sub("[A-Za-z]+", "", instance["Lyric"])
            else:
                instance["Lyric"] = romkan.to_katakana(instance["Lyric"])
            instance["Lyric"] = re.sub(u"[^ァ-ン]",  "",  unicode(instance["Lyric"])).encode("utf8")
        instance["Tempo"] = str(bpm)
        if "NoteNum" in instance:
            if instance["Lyric"] == "":
                instance["NoteNum"] = "rest"
            song.append(instance)
    return song

def open_text(file_name):
    song = []
    block = []
    for strm in open(file_name, "r"):
        if strm.strip().startswith("@eol"):
            sys.stderr.write("error1\n")
            exit(1)
        if strm.strip().startswith("@title"):
            if (strm.strip().split(" ")[0] != "@title"):
                sys.stderr.write("error2\n")
                exit(1)
            title = " ".join(strm.strip().split(" ")[1::])
            continue
        if strm.strip().startswith("@artist"):
            if (strm.strip().split(" ")[0] != "@artist"):
                sys.stderr.write("error3\n")
                exit(1)
            artist = " ".join(strm.strip().split(" ")[1::])
            continue
        if strm.strip() == "":
            if len(block) > 0:
                song.append(block[::])
                block = []
        else:
            block.append(" ".join(strm.strip().split("-")))
    if len(block) > 0:
        song.append(block[::])
        block = []
    song_lyrics = {"artist":artist, "title":title, "lyrics":[]}
    for block in song:
        block_lyrics = []
        for line in block:
            line_lyrics = []
            for morph in parse(line.encode('utf-8')):
                sur = morph.split("\t")[0]
                morph_info = morph.split("\t")[1].split(",")
                if len(morph_info) <= 7: continue
                pos = morph_info[0]
                dtl = morph_info[1]
                kana = morph_info[-2]
                acc = morph_info[-1].split("_")
                if re_katakana.search(unicode(kana)):
                    pass
                else:
                    continue
                yomi = kana.split("_")
                line_lyrics.append((sur, pos, dtl, yomi, acc))
            block_lyrics.append(line_lyrics)
        song_lyrics["lyrics"].append(block_lyrics[::])
    return song_lyrics

"""
alignment function. (see alignment.py)
"""
def align(ust_kana, lyrics_kana):
    return alignment.needle(ust_kana, lyrics_kana)

def make_data(dir_name):
    """ Step1: Parse UTAU """
    ust_files = glob.glob(dir_name + "/*.ust")
    if len(ust_files) != 1:
        sys.stderr.write("Error! Number ot ust txt file is not 1.")
        exit(1)
    ust_file = ust_files[0]
    song_ust = open_ust(ust_file)
    yomi_ust = []
    for inst in song_ust:
        if inst["NoteNum"] == "rest":
            yomi_ust.append("R")
        else:
            yomi_ust.append(inst["Lyric"])

    """ Step2: Parse Text """
    lyrics_files = glob.glob(dir_name + "/*.txt")
    if len(lyrics_files) != 1:
        sys.stderr.write("Error! Number ot lyrics txt file is not 1.")
    lyrics_file = lyrics_files[0]
    song_text = open_text(lyrics_file)
    yomi2word = {}
    word2yomi = {}
    yomi_text = []
    word_text = []
    yomi_idx = 0
    word_idx = 0
    eob_idx = set()
    eol_idx = set()
    for block in song_text["lyrics"]:
        for line in block:
            for word in line:
                word_text.append(word)
                for yomi in word[-2]:
                    yomi_text.append(yomi)
                    yomi2word[yomi_idx] = word_idx
                    word2yomi[word_idx] = yomi_idx
                    yomi_idx += 1
                word_idx += 1
            word_text.append(("<l>", "<l>", "<l>", []))
            eol_idx.add(word_idx)
            word_idx += 1
        word_text.pop(-1)
        word_text.append(("<b>", "<b>", "<b>", []))
        eob_idx.add(word_idx-1)
        eol_idx.remove(word_idx-1)

    """ Step3: Align """
    align_ust, align_lyrics = align(yomi_ust, yomi_text)

    """ Step4: Make Data """
    yomi_idx = 0
    note_idx = 0
    temp_lyrics = []
    cut_eob = False
    cut_eol = False
    for y_ust, y_text in zip(align_ust, align_lyrics):
        if y_ust == "-":
            if yomi2word[yomi_idx]-1 in eob_idx:
                cut_eob = True
            if yomi2word[yomi_idx]-1 in eol_idx:
                cut_eol = True
        elif y_ust == "R":
            temp_lyrics.append([note_idx, 
                                song_ust[note_idx]["NoteNum"], 
                                song_ust[note_idx]["Length"], 
                                "<None>", 
                                "<None>", 
                                "<None>", 
                                "<None>"])
            #print note_idx, song_ust[note_idx]["NoteNum"], song_ust[note_idx]["Length"]
        else:
            if y_text == "-":
                temp_lyrics.append(["hoge", note_idx, song_ust[note_idx]["NoteNum"], song_ust[note_idx]["Length"], y_ust])
            else:
                if yomi2word[yomi_idx]-1 in eol_idx:
                    cut_eol = False
                    cut_eob = False
                    temp_lyrics.append([note_idx, 
                                        song_ust[note_idx]["NoteNum"], 
                                        song_ust[note_idx]["Length"], 
                                        y_ust, 
                                        word_text[yomi2word[yomi_idx]], 
                                        yomi2word[yomi_idx], 
                                        "<BOL>"])
                    #print note_idx, song_ust[note_idx]["NoteNum"], song_ust[note_idx]["Length"], y_ust, word_text[yomi2word[yomi_idx]][0], yomi2word[yomi_idx], "<BOL>"
                elif yomi2word[yomi_idx]-1 in eob_idx:
                    cut_eol = False
                    cut_eob = False
                    temp_lyrics.append([note_idx, 
                                        song_ust[note_idx]["NoteNum"], 
                                        song_ust[note_idx]["Length"], 
                                        y_ust, 
                                        word_text[yomi2word[yomi_idx]], 
                                        yomi2word[yomi_idx], 
                                        "<BOB>"])
                    #print note_idx, song_ust[note_idx]["NoteNum"], song_ust[note_idx]["Length"], y_ust, word_text[yomi2word[yomi_idx]][0], yomi2word[yomi_idx], "<BOB>"
                else:
                    tag = '<None>'
                    if cut_eol == True:
                        tag = "<BOL>"
                        cut_eol = False
                    if cut_eob == True:
                        tag = "<BOB>"
                        cut_eob = False
                    if len(temp_lyrics) > 0:
                        if temp_lyrics[-1][-2] == yomi2word[yomi_idx]:
                            tag = temp_lyrics[-1][-1]
                    temp_lyrics.append([note_idx, 
                                        song_ust[note_idx]["NoteNum"], 
                                        song_ust[note_idx]["Length"], 
                                        y_ust, 
                                        word_text[yomi2word[yomi_idx]], 
                                        yomi2word[yomi_idx], 
                                        tag])
                    #print note_idx, song_ust[note_idx]["NoteNum"], song_ust[note_idx]["Length"], y_ust, word_text[yomi2word[yomi_idx]][0], yomi2word[yomi_idx], tag
        if y_text != "-":
            yomi_idx += 1
        if y_ust != "-":
            note_idx += 1
    assert len(song_ust) == len(temp_lyrics), "nb of note error."
    
    """ Step5: Fill Rest """
    old_note_info = []
    filled_lyrics = []
    for note_info in temp_lyrics:
        if note_info[0] == 'hoge':
            if len(old_note_info) == 0:
                filled_lyrics.append([note_info[1], 'rest', note_info[3], '<None>', '<None>', '<None>', '<None>'])
            elif old_note_info[1] == 'rest':
                filled_lyrics.append([note_info[1], 'rest', note_info[3], '<None>', '<None>', '<None>', '<None>'])
            else:
                filled_lyrics.append([note_info[1], note_info[2], note_info[3], get_long_sound(old_note_info[3]), old_note_info[4], old_note_info[5], old_note_info[6]])
        else:
            filled_lyrics.append(note_info[::])
        #print " ".join([str(i) for i in filled_lyrics[-1]])
        old_note_info = filled_lyrics[-1]
    assert len(song_ust) == len(filled_lyrics), "nb of note error."

    """ Step6: Merge rest """
    merge_lyrics = []
    stack_rest = []
    for note_info in filled_lyrics:
        if note_info[1] == 'rest':
            stack_rest.append(note_info[::])
        else:
            if len(stack_rest) > 0:
                rest_length = 0
                for rest in stack_rest:
                    rest_idx = rest[0]
                    rest_length += int(rest[2])
                stack_rest = []
                merge_lyrics.append([rest_idx, 'rest', str(rest_length), '<None>', '<None>', '<None>', '<None>'])
            merge_lyrics.append(note_info[::])
        #print " ".join([str(i) for i in note_info])

    """ Step7: add long rest note """
    if merge_lyrics[0][1] == 'rest':
        merge_lyrics[0][2] = '7680'
    else:
        merge_lyrics.insert(0, ['0', 'rest', '7680', '<None>', '<None>', '<None>', '<None>'])
    if merge_lyrics[-1][1] == 'rest':
        merge_lyrics[-1][2] = '7680'
    else:
        merge_lyrics.append(['0', 'rest', '7680', '<None>', '<None>', '<None>', '<None>'])

    """ Step8: align index """
    final_lyrics = []
    for i, note_info in enumerate(merge_lyrics):
        final_lyrics.append([i] + note_info[1::])
        #print " ".join([str(i) for i in final_lyrics[-1]])

    """ Step9: add initial word BOB """
    first_word_id = final_lyrics[1][5]
    for i, note_info in enumerate(final_lyrics):
        word_id = note_info[5]
        if first_word_id == word_id:
            final_lyrics[i][6] = '<BOB>'
        #print " ".join([str(i) for i in final_lyrics[i]])

    """ Step10: Update word infomation if rests are located in word """
    for i, note_info in enumerate(final_lyrics[:-1:]):
        if note_info[1] == 'rest':
            if final_lyrics[i-1][5] == final_lyrics[i+1][5]:
                final_lyrics[i][4] = final_lyrics[i-1][4]
                final_lyrics[i][5] = final_lyrics[i-1][5]
                final_lyrics[i][6] = final_lyrics[i-1][6]
        pr = []
        for a, l in enumerate(final_lyrics[i]):
            if a != 4:
                pr.append(str(l))
            else:
                pr.append("(" + l[0] + " "+ l[1] + " " + l[2] + " [" + " ".join(l[3]) + "] [" + " ".join(l[4]) + "]")
        #print " ".join(pr)
    return {"artist":song_text["artist"], "title":song_text["title"], "lyrics":final_lyrics}

def main(args):
    for dir_name in glob.glob(args.data.rstrip("/") + "/*"):
        data = make_data(dir_name)
        print json.dumps(data, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data", dest="data", default="./pair_data/", type=str, help="data folder")
    args = parser.parse_args()
    main(args)
