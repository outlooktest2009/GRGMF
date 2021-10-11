
import os
import numpy as np
# from functions import *
from collections import defaultdict
import pandas as pd


def load_drug_target_pairs(file_path):
    int_pairs = defaultdict(list)
    with open(file_path, "r") as inf:
        for line in inf:
            data = line.strip('\n').split()
            if len(data) > 1:
                int_pairs[data[0]] = data[1:]
    return int_pairs


def load_metador_interaction_data(file_path):
    matador = defaultdict(list)
    with open(file_path, "r") as inf:
        next(inf)
        for line in inf:
            data = line.strip('\n').split('\t')
            matador[data[0]].extend(data[6].split())
    return matador


def load_keggid_map(database_folder):
    pubMap = {}
    with open(os.path.join(database_folder, "pubchem_SIDs_to_CIDs.txt"), "r") as inf:
        next(inf)
        for line in inf:
            sid, cid = line.strip('\n').split()
            pubMap[sid] = cid

    drugMap = defaultdict(dict)
    with open(os.path.join(database_folder, "kegg_drug_map.txt"), "r") as inf:
        next(inf)
        for line in inf:
            k, d, c, p, ch = line.strip('\n').split('$')
            if d != " ":
                drugMap[k]["drugbank"] = d.split()
            if c != " ":
                drugMap[k]["CHEMBL"] = c.split()
            if p != " ":
                drugMap[k]["PubChemCID"] = [pubMap[sid] for sid in p.split() if sid in pubMap]

    targetMap = defaultdict(dict)
    with open(os.path.join(database_folder, "target_kegg_uniprot.txt"), "r") as inf:
        next(inf)
        for line in inf:
            data = line.strip().split()
            if len(data) > 1:
                targetMap[data[0]]["uniprot"] = data[1:]
    with open(os.path.join(database_folder, "target_kegg_chembl.txt"), "r") as inf:
        next(inf)
        for line in inf:
            data = line.strip().split()
            if len(data) > 1:
                targetMap[data[0]]["chembl"] = data[1:]
    return drugMap, targetMap


def verify_drug_target_interactions(pairs, kegg, drugbank, chembl, matador, drugMap, targetMap, output_file):
    conf_pairs = []
    outf = open(output_file, "w")
    for num in range(len(pairs)):
        d, t, v = pairs[num]
        if d in kegg:
            if t in kegg[d]:
                k_value = 1
            else:
                k_value = 0
        else:
            k_value = 0
        try:
            x = 0
            for dm in drugMap[d]["drugbank"]:
                for t1 in targetMap[t]["uniprot"]:
                    if t1 in drugbank[dm]:
                        x += 1
            if x > 0:
                d_value = 1
            else:
                d_value = 0
        except:
            d_value = 0
        try:
            x = 0
            for dm in drugMap[d]["CHEMBL"]:
                for t1 in targetMap[t]["chembl"]:
                    if t1 in chembl[dm]:
                        x += 1
            if x > 0:
                c_value = 1
            else:
                c_value = 0
        except:
            c_value = 0

        try:
            x = 0
            for dm in drugMap[d]["PubChemCID"]:
                for t1 in targetMap[t]["uniprot"]:
                    if t1 in matador[dm]:
                        x += 1
            if x > 0:
                m_value = 1
            else:
                m_value = 0
        except:
            m_value = 0
        if k_value == 1:
            k_str = "K"
        else:
            k_str = " "

        if c_value == 1:
            c_str = "C"
        else:
            c_str = " "

        if d_value == 1:
            d_str = "D"
        else:
            d_str = " "

        if m_value == 1:
            m_str = "M"
        else:
            m_str = " "
        num += 1
        if k_value+d_value+c_value+m_value > 0:
            conf_pairs.append((d, t, 1))
        else:
            conf_pairs.append((d, t, 0))
        outf.write("\t\t".join([str(num), d, t, str(np.round(v, 4)), c_str, d_str, k_str, m_str])+"\n")
    outf.close()
    return conf_pairs


def novel_prediction_analysis(predict_pairs, output_file, database_folder, positions=[10, 30, 50, 100, 200, 500, 1000]):
    drugMap, targetMap = load_keggid_map(database_folder)
    kegg = load_drug_target_pairs(os.path.join(database_folder, "kegg.txt"))
    drugbank = load_drug_target_pairs(os.path.join(database_folder, "drugbank.txt"))
    cheml = load_drug_target_pairs(os.path.join(database_folder, "chembl.txt"))
    matador = load_metador_interaction_data(os.path.join(database_folder, "matador.tsv"))
    verify_pairs = verify_drug_target_interactions(predict_pairs, kegg, drugbank, cheml, matador, drugMap, targetMap, output_file)
    inx = np.array(positions)
    vec = np.zeros(inx.size)
    num_pairs = len(verify_pairs)
    for i in range(num_pairs):
        d, t, v = verify_pairs[i]
        if v > 0:
            ii = ((i+1) <= inx)
            vec[ii] += 1.0
    for i, p in enumerate(positions):
        if p <= num_pairs:
            print(("Top-%s novel DTIs, NO. confirmed:%s, Percentage:%.2f%%" % (p, int(vec[i]), vec[i]*100/inx[i])))

def MDA_novel_prediction_analysis(predict_pairs: pd.DataFrame, output_file, case_disease, database_folder):
    dbDEMC = pd.read_csv(os.path.join(database_folder, case_disease + '_dbDEMC.csv'))
    hmdd3 = pd.read_csv(os.path.join(database_folder, case_disease + '_hmdd3.csv'))
    if os.path.exists(os.path.join(database_folder, case_disease + '_miRCancer.csv')):
        miRCan = pd.read_csv(os.path.join(database_folder, case_disease + '_miRCancer.csv'))

    val_c = 0
    flag = [[] for i in range(len(predict_pairs))]
    for i in range(len(predict_pairs)):
        mir, dis, score = predict_pairs.iloc[i]
        miR = mir.replace('mir', 'miR')
        if dbDEMC['miRNA_ID'].str.contains('^' + miR).any():
            flag[i].append('dbDEMC')
        if hmdd3['mir'].str.contains('^' + mir).any():
            flag[i].append('HMDD3.0')
        if os.path.exists(os.path.join(database_folder, case_disease + '_miRCancer.csv')):
            if miRCan['mirId'].str.contains('^' + mir).any():
                flag[i].append('miRCancer')
        if len(flag[i])>0:
            val_c += 1
        else:
            flag[i].append('unconfirmed')
    print("Validated number: %d, Percentage: %.3f" %(val_c, val_c/len(predict_pairs)))

    flag = list(map(lambda x:','.join(x), flag))

    predict_pairs.insert(loc=3, column='Evidence', value=flag)
    predict_pairs.to_csv(path_or_buf=output_file,index=False)


def MDA_novel_top_bottom_analysis(tops: pd.DataFrame, bottoms: pd.DataFrame, output_file, case_disease,
                                  database_folder):
    _tops = tops.copy()
    _bottoms = bottoms.copy()
    dbDEMC = pd.read_csv(os.path.join(database_folder, case_disease + '_dbDEMC.csv'))
    hmdd3 = pd.read_csv(os.path.join(database_folder, case_disease + '_hmdd3.csv'))
    if os.path.exists(os.path.join(database_folder, case_disease + '_miRCancer.csv')):
        miRCan = pd.read_csv(os.path.join(database_folder, case_disease + '_miRCancer.csv'))

    val_c = 0
    flag = [[] for i in range(len(_tops))]
    for i in range(len(_tops)):
        mir, dis, score = _tops.iloc[i]
        miR = mir.replace('mir', 'miR')
        if dbDEMC['miRNA_ID'].str.contains('^' + miR).any():
            flag[i].append('dbDEMC')
        if hmdd3['mir'].str.contains('^' + mir).any():
            flag[i].append('HMDD3.0')
        if os.path.exists(os.path.join(database_folder, case_disease + '_miRCancer.csv')):
            if miRCan['mirId'].str.contains('^' + mir).any():
                flag[i].append('miRCancer')
        if len(flag[i]) > 0:
            val_c += 1
        else:
            flag[i].append('unconfirmed')
    print("Validated number: %d, Percentage: %.1f" % (val_c, val_c / len(_tops)))
    flag = list(map(lambda x: ','.join(x), flag))
    _tops.insert(loc=3, column='Evidence(top)', value=flag)

    val_c = 0
    flag2 = [[] for i in range(len(_bottoms))]
    for i in range(len(_bottoms)):
        mir, dis, score = _bottoms.iloc[i]
        miR = mir.replace('mir', 'miR')
        if dbDEMC['miRNA_ID'].str.contains('^' + miR).any():
            flag2[i].append('dbDEMC')
        if hmdd3['mir'].str.contains('^' + mir).any():
            flag2[i].append('HMDD3.0')
        if os.path.exists(os.path.join(database_folder, case_disease + '_miRCancer.csv')):
            if miRCan['mirId'].str.contains('^' + mir).any():
                flag2[i].append('miRCancer')
        if len(flag2[i]) > 0:
            val_c += 1
        else:
            flag2[i].append('unconfirmed')
    print("Validated number: %d, Percentage: %.1f" % (val_c, val_c / len(_bottoms)))
    flag2 = list(map(lambda x: ','.join(x), flag2))
    _bottoms.insert(loc=3, column='Evidence(bottom)', value=flag2)
    tops_bottoms = _tops.append(_bottoms, sort=False)
    tops_bottoms.to_csv(path_or_buf=output_file, index=False)
    return tops_bottoms