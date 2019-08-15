# -*- coding: utf-8 -*-
# For python2
import sys
import glob
import alignment
import json
import romkan               # pip install
import jaconv               # pip install
from jcconv import *        # pip install
from collections import defaultdict

from stanford_corenlp_pywrapper import CoreNLP          # git clone https://github.com/brendano/stanford_corenlp_pywrapper
corenlp_dir = "./stanford-corenlp-full-2013-06-20/"     # wget http://nlp.stanford.edu/software/stanford-corenlp-full-2013-06-20.zip
proc = CoreNLP(configdict={'annotators': 'tokenize,ssplit,pos,lemma'},  corenlp_jars=["./stanford-corenlp-full-2013-06-20/*"])

import re
hira_p = re.compile(u"[ぁ-ん]")
kata_p = re.compile(u"[ァ-ン]")
en_p = re.compile(ur"[a-zA-Z\']")
num_p = re.compile(ur"[0-9\']")

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
        if len(morph.split("\t")) <= 8:break        
        if morph == "EOS" or morph == "": continue
        mora = get_mora(morph.split("\t")[1])
        pos = morph.split("\t")[4].split("-")[0]
        if morph.split("\t")[7] == "":
            acc_position = 0        
        else:
            acc_position = int(morph.split("\t")[7].split(",")[0])
        if morph.split("\t")[8] == "":
            acc_joint = None
        else:
            acc_joint = morph.split("\t")[8]
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
        # step1: accent rule
        if acc_joint:
            if acc_joint[0] == "P":
                head_f = True
            else:
                if len(accent_info) == 0:
                    out_accent = acc_position
                else:
                    prev_acc_joint = accent_info[-1][2]
                    prev_pos = accent_info[-1][4]
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
                    elif len(acc_joint.split(",")[0].split("%")) > 1:
                        acc_joints = acc_joint.split(",")
                        for j in xrange(len(acc_joints)):
                            sub_rule = acc_joints[j]
                            if j+1 < len(acc_joints):
                                if len(acc_joints[j].split("%")) == 1:
                                    continue
                                if len(acc_joints[j+1].split("%")) == 1:
                                    sub_rule = acc_joints[j] + "," + acc_joints[j+1]
                            if len(sub_rule.split("%")) == 1: continue  
                            sub_rule_pos = sub_rule.split("%")[0]
                            sub_rule_F = sub_rule.split("%")[1]
                            if sub_rule_pos in prev_pos:
                                F = sub_rule_F.split("@")[0]
                                if F == "F1":   
                                    pass
                                elif F == "F2":     # 不完全支配型
                                    joint_value = int(sub_rule_F.split("@")[1].split(",")[0])
                                    if out_accent == 0:  
                                        out_accent = out_mora +  joint_value
                                elif F == "F3":     # 融合型
                                    joint_value = int(sub_rule_F.split("@")[1].split(",")[0])
                                    if out_accent != 0:  
                                        out_accent = out_mora + joint_value
                                elif F == "F4":     # 支配型 
                                    joint_value = int(sub_rule_F.split("@")[1].split(",")[0])
                                    out_accent = out_mora + joint_value
                                elif F == "F5":     # 平板型 
                                    out_accent = 0
                                elif F == "F6": 
                                    joint_value1 = int(sub_rule_F.split("@")[1].split(",")[0])
                                    joint_value2 = int(sub_rule_F.split("@")[1].split(",")[1])
                                    if out_accent == 0:  
                                        out_accent = out_mora + joint_value1
                                    else:  
                                        out_accent = out_mora + joint_value2
                                break
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
            if len(accent_info) == 0:       
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
    else:
        hl.append("L")
        for i in xrange(out_accent-1):
            hl.append("H")
        for i in xrange(out_mora-out_accent):
            hl.append("L")
    return hl


"""
lyrics parsing functions
"""
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
        kana = en2kana.get(sur.lower().encode("utf8"), sur.encode("utf8"), "*")
        yomi = kana
        return "%s\t%s,%s,%s,%s,%s,%s,%s,%s,%s"%(sur, pos, pos2, pos3, pos4, form1, form2, base, kana, yomi)

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
                syllable_lyrics["sur"] = w_a[0]
                syllable_lyrics["roma"] = w_a[1]
                syllable_lyrics["accent"] = "*"
            else:
                if len(accent) <= mora:      
                    syllable_lyrics["sur"] = w_a[0]
                    syllable_lyrics["roma"] = w_a[1]
                    syllable_lyrics["accent"] = accent[-1]
                else:
                    syllable_lyrics["sur"] = w_a[0]
                    syllable_lyrics["roma"] = w_a[1]
                    syllable_lyrics["accent"] = accent[acc_idx]
                acc_idx += 1
            word_lyrics["syllable"].append(syllable_lyrics)
        phrase_lyrics["word"].append(word_lyrics)
    return phrase_lyrics

def get_morph(line):
    line_lyrics = {"sur":line.strip(), "phrase":[]}
    phrase = []
    for morph in cabocha_tagger.parseToString(line.encode("utf8")).split("\n"):
        if morph.strip() == "" or morph.strip() == "EOS": continue
        if morph.strip().split(" ")[0] == "*":
            if phrase:
                phrase_lyrics = get_phrase(phrase, phrase_info)
                phrase = []
                line_lyrics["phrase"].append(phrase_lyrics)
            phrase_info = morph.split(" ")[1::]
        else:
            phrase.append(morph)
    phrase_lyrics = get_phrase(phrase, phrase_info)
    phrase = []
    line_lyrics["phrase"].append(phrase_lyrics)
    return line_lyrics

def get_mora(kana):
    mora = len(unicode(kana))
    for char in unicode(kana):
        if char in ('ァ', 'ィ', 'ゥ', 'ェ', 'ォ', 'ャ', 'ュ', 'ョ'):
            mora -= 1
    if mora < 0:
        mora = 0
    return mora

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


"""
melodies parsing functions
Length: 1920: whole note
Length: 480: quarter note
Length: 240: eighth note
Length: 120: sixteenth note
"""
def get_beat2time(currentBeat):     # convert current beat to current time
    total_secons = 0.0
    for bpm, beat in currentBeat.iteritems():
        spb = 60.0/bpm
        num_of_beat = beat/480.0
        seconds = num_of_beat*spb
        total_secons += seconds
    return total_secons

def get_beat2rhythm(currentBeat):
    B = sum(currentBeat.itervalues())
    if B%1920 == 0:
        return "1"
    elif B%1920 == 480:
        return "2"
    elif B%1920 == 960:
        return "3"
    elif B%1920 == 1440:
        return "4"
    else:
        return "-"

"""
parse UST.
you need to convert original UST's character code (SHIFT-jis) to (UTF8)
"""
def open_ust(file_name):
    song = []
    instance = {}
    currentBeat = defaultdict(float)        
    bpm = 0.0
    currentTime = 0.0
    for strm in open(file_name, "r"):
        if strm.strip().startswith("["):
            if len(instance) > 0:
                if instance.get("Tempo", None):
                    bpm = float(".".join(instance["Tempo"].split(",")))
                if instance.get("Length", None):
                    currentTime = get_beat2time(currentBeat)
                    instance["StartTime"] = currentTime 
                    currentRhythm = get_beat2rhythm(currentBeat)
                    instance["Beat"] = currentRhythm
                    currentBeat[bpm] += float(instance["Length"]) 
                    m, s = divmod(currentTime, 60)
                    h, m = divmod(m, 60)
                    instance["StartTimeReadable"] = "%d/%d/%s"%(h, m, s)
                    instance["Duration"] = str(60.0/bpm*(float(instance["Length"])/480.0))
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
                song.append(instance)
            instance = {"InstanceIdx": strm.strip().lstrip("[#").rstrip("]")}
        else:
            if len(strm.strip().split("=")) < 2:
                continue
            key, value = strm.strip().split("=")
            if key == "Lyric":
                value = jaconv.hira2kata(unicode(value)).encode("utf8")
            instance[key] = value

    if len(instance) > 0:
        if instance.get("Tempo", None):
            bpm = float(".".join(instance["Tempo"].split(",")))
        if instance.get("Length", None):
            currentTime = get_beat2time(currentBeat)
            instance["StartTime"] = currentTime 
            currentRhythm = get_beat2rhythm(currentBeat)
            instance["Beat"] = currentRhythm
            currentBeat[bpm] += float(instance["Length"])
            m, s = divmod(currentTime, 60)
            h, m = divmod(m, 60)
            instance["StartTimeReadable"] = "%d/%d/%s"%(h, m, s)
            instance["Duration"] = str(60.0/bpm*(float(instance["Length"])/480.0))
        if instance.get("Lyric", None):     # extract HIRAGANA (NOTE: Sometimes VOCALOID-specific characters are included)
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
        song.append(instance)
    return song

"""
alignment function. (see alignment.py)
"""
def align(ust_kana, lyrics_kana):       #Needleman-Wunsch alignment
    return alignment.needle(ust_kana, lyrics_kana)

def make_data(dir_name):
    """ assertion  """
    dir_name = "./pair_data/" + dir_name
    lyrics_files = glob.glob(dir_name + "/*.txt")
    if len(lyrics_files) != 1:
        sys.stderr.write("Error! Number ot lyrics txt file is not 1.")
        exit(1)
    lyrics_file = lyrics_files[0]
    ust_files = glob.glob(dir_name + "/*.ust")
    if len(ust_files) != 1:
        sys.stderr.write("Error! Number ot ust txt file is not 1.")
        exit(1)
    ust_file = ust_files[0]
    """ parse data  """
    song_ust = open_ust(ust_file)
    ust_kana = [inst.get("Lyric", " ") for inst in song_ust]
    """ convert data format """
    song = []
    block = []
    for strm in open(lyrics_file, "r"):
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
    """ convert data format 2 """
    song_lyrics = {"artist":artist, "title":title, "song":[]}
    for block in song:
        block_lyrics = []
        for line in block:
            line_lyrics = get_morph(line)
            block_lyrics.append(line_lyrics)
        song_lyrics["song"].append(block_lyrics[::])
    """ extract KATAKANA seqence """
    lyrics_kana = []
    for block in song_lyrics["song"]:
        for line in block:
            for phrase in line["phrase"]:
                for word in phrase["word"]:
                    for syllable in word["syllable"]:
                        kana = syllable["sur"]
                        lyrics_kana.append(kana.encode("utf8"))
    """ alighn notes and strings """
    new_ust_kana = []
    for kana in ust_kana:
        if kana == "" or kana == "　" or kana == " ":
            new_ust_kana.append("R")
        else:
            new_ust_kana.append(kana)
    new_lyrics_kana = []
    for kana in lyrics_kana:
        if kana == "" or kana == "　" or kana == " ":
            new_lyrics_kana.append("R")
        else:
            new_lyrics_kana.append(kana)
    align_ust, align_lyrics = align(new_ust_kana, new_lyrics_kana)
    align_idx = 0
    ust_idx = 0
    align2ust = {}
    for align_idx, ust in enumerate(align_ust):
        if ust == "-":
            pass
        else:
            align2ust[align_idx] = ust_idx
            ust_idx += 1
    """ print result """
    num_correct_align = 0.0
    num_align = 0.0
    align_idx = 0
    print "@bos\tartist:%s\ttitle:%s"%(song_lyrics["artist"], song_lyrics["title"])
    for block in song_lyrics["song"]:
        print "@bob"
        for line in block:
            print "@bol\t%s"%line["sur"]
            for phrase in line["phrase"]:
                print "@bop\t%s\t%s"%(phrase["sur"], phrase["info"])
                for word in phrase["word"]:
                    print "@bow\t%s"%(word["info"])
                    for syllable in word["syllable"]:
                        while True:
                            if align_lyrics[align_idx] == "-":
                                align_idx += 1
                            else:
                                break
                        if align_idx in align2ust:
                            params = []
                            for key in song_ust[align2ust[align_idx]].keys():
                                if "Piches" not in key and "Pitches" not in key and "Pitch" not in key:
                                    if key == "StartTime":
                                        StartTime = float(song_ust[align2ust[align_idx]][key])
                                        #EndTime = StartTime + song_ust[align2ust[align_idx]]["Duration"]
                                        m, s = divmod(StartTime, 60)
                                        h, m = divmod(m, 60)
                                        StartTimeReadable = "%d/%d/%s"%(h, m, s)
                                        params.append("StartTime:%s"%StartTime)
                                        params.append("StartTimeReadable:%s"%StartTimeReadable)
                                    elif key == "StartTimeReadable":
                                        pass
                                    else:
                                        params.append("%s:%s"%(key, song_ust[align2ust[align_idx]][key]))
                            param = " ".join(params)
                            print "\tSur:%s Roma:%s Accent:%s %s"%(syllable["sur"], syllable["roma"], syllable["accent"], param)
                            if kata_p.search(unicode(syllable["sur"])):
                                num_align += 1.0
                                if syllable["sur"] == song_ust[align2ust[align_idx]].get("Lyric", None):
                                    num_correct_align += 1.0
                                elif syllable["sur"] == "ッ" and song_ust[align2ust[align_idx]].get("Lyric", "hoge") == "":
                                    num_correct_align += 1.0
                                elif syllable["sur"] in ("オ", "ヲ") and song_ust[align2ust[align_idx]].get("Lyric", "hoge") in ("オ", "ヲ"):
                                    num_correct_align += 1.0
                                elif syllable["sur"] in ("ズ", "ヅ") and song_ust[align2ust[align_idx]].get("Lyric", "hoge") in ("ズ", "ヅ"):
                                    num_correct_align += 1.0
                        else:
                            print "\tSur:%s Roma:%s Accent:%s"%(syllable["sur"], syllable["roma"], syllable["accent"])
                            if kata_p.search(unicode(syllable["sur"])):
                                num_align += 1.0
                        align_idx += 1
                    print "@eow"
                print "@eop"
            print "@eol"
        print "@eob"
    print "@eos"
    """ return alignment match rate """
    return num_correct_align/num_align



def main():
    dir_path="./pair_data/*"
    scores = defaultdict(float)
    for i, dir_name in enumerate(glob.glob(dir_path)):
        dir_name = dir_name.split("/")[-1]
        try:
            score = make_data(dir_name)
            sys.stderr.write("score:%s\tnum:%s\tname:%s\n"%(score, i, dir_name))
            scores[dir_name] = score
        except KeyboardInterrupt:
            print "@error:%s"%dir_name
    score_file = open("score.txt", "w")
    for d, s in scores.iteritems():
        score_file.write("dir_name:%s\tscore:%s\n"%(d, s))
    score_file.write("average_score:%s\n"%(sum(scores.values())/float(len(scores))))


if __name__ == "__main__":
    main()

