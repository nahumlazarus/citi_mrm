import os
# http://localhost:8888/?token=495e95ef991ce30af09d989ac52dbedebce0a11696e89599
import numpy as np
import seaborn as sns
import pandas as pd
import re
import yaml
import glob
import matplotlib.pyplot as plt
# import os
import logging
import logging.config
import shutil
from tqdm.notebook import tqdm
from ipywidgets import VBox,HBox,interactive_output,Label,Dropdown
from IPython.display import HTML
from datetime import datetime
from sklearn.metrics import accuracy_score
import subprocess
# from subprocess_funcs import run_bat_file
sns.set_style('whitegrid')
sns.set_context('talk')
plt.rcParams['figure.figsize'] = [9,7]
pd.options.display.max_colwidth = 300
logging.config.fileConfig('logger.ini')
logger = logging.getLogger("research")
from typing import Iterable


# Folder setup: In Testing dir, create one folder per test run
# One test run per "setup" - e.g. 
# Scenarios: 1. Single model, 2                                 

def run_bat_file(bat_file_path: str):
    proc1 = subprocess.run(bat_file_path, shell=True)
    bat_fn = os.path.basename(bat_file_path)

    if proc1.returncode == 0:
        logger.info(f'{bat_fn} complete.')
    else:
        logger.info(f'Error running {bat_fn}')
        return 

# def print_model_run_bat(bat_file: str, model_level: str, model_path: str, date: str, dset_output_dir: str, testfiles_p: str):
#     exe_p = r"N:\NxResearch\Complaints\035_Test2020Classifier_2023Data\EXE\NXPredictiveModel_10.8\NXPredictiveModelClass-InternalBeta.exe"
#     class_dir = os.path.join(model_path, "Classifier_Prod") if 'Classifier_Prod' in os.listdir(model_path) else os.path.join(model_path, "Classifier")
#     cli_file = os.path.join(class_dir, 'model_def.cli')
#     test_suff = f'{model_level}_{date}'
#     rep_name = f'stm_output_{test_suff}.csv'
#     class_rep_name = f'class_output_{test_suff}.csv'
#     res_path = os.path.join(dset_output_dir, class_rep_name)

#     print(f'@REM @echo off', file=bat_file)
#     print(f'REM {exe_p}\n', file=bat_file)
#     print(f'{exe_p} ^', file=bat_file)
#     print(f'\t--filelist {testfiles_p} ^', file=bat_file)
#     print(f'\t--clifile {cli_file} ^', file=bat_file)
#     print(f'\t--classifier-directory {class_dir} ^', file=bat_file)
#     print(f'\t--report-name {rep_name} ^', file=bat_file)
#     print(f'\t--log classifier_taxonomy.log ^', file=bat_file)
#     print(f'\t--classifier-report-name {class_rep_name} ^', file=bat_file)
#     print(f'\t--use-correct-report-header ^', file=bat_file)
#     print(f'\t--outputdir {dset_output_dir} ^', file=bat_file)
#     print(f'\t-ma 3', file=bat_file)
#     print(f'\n', file=bat_file)
#     return res_path


# 1 dataset, 1 model - save results to model path
# 1 dataset, many models - save each result to each model path
# many datasets, 1 model
# many datasets, many models


# def create_multiclass_bat(data_dict: dict, model_paths: dict, bat_path: str, testrun_name: str=None):
#     if not os.path.exists(output_dir):
#         os.mkdir(output_dir)
#     date = datetime.now().strftime('%m-%d-%y')
#     # bat_name = f'_step1_multiclass_{testrun_name}_{date}.bat' if testrun_name else f'_step1_multiclass_{date}.bat'
#     # bat_fp = os.path.join(output_dir, bat_name)
#     test_results_paths = {}
#     with open(bat_path,'wt') as f:
#         for k, v in data_dict.items():
#             dset_output_dir = os.path.join(output_dir, k)
#             if not os.path.exists(dset_output_dir):
#                 os.mkdir(dset_output_dir)
#             testfiles_p = os.path.join(dset_output_dir, 'testFiles.txt')
#             # testfiles_p = f'{output_dir}/{k}_testFiles.txt'
#             v.to_csv(testfiles_p, header=False, index=False, sep='\t')
#             testset_res_paths = {}
#             for l, model_path in model_paths.items():
#                 testset_res_paths[l] = print_model_run_bat(f, l, model_path, date, dset_output_dir, testfiles_p)
#             test_results_paths[k] = testset_res_paths
#     print(bat_fp)
#     print(test_results_paths)
#     return bat_fp, test_results_paths



def create_multimodel_bat(data_dict: dict, model_paths: dict, testrun_name: str, output_dir: str):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    exe_p = r"N:\NxResearch\Complaints\035_Test2020Classifier_2023Data\EXE\NXPredictiveModel_10.8\NXPredictiveModelClass-InternalBeta.exe"
    date = datetime.now().strftime('%m-%d-%y')
    bat_fp = f'{output_dir}/_step1_multiclass_{testrun_name}_{date}.bat'
    test_results_paths = {}
    with open(bat_fp,'wt') as f:
        for k, v in data_dict.items():
            dset_output_dir = os.path.join(output_dir, k)
            if not os.path.exists(dset_output_dir):
                os.mkdir(dset_output_dir)
            testfiles_p = os.path.join(dset_output_dir, 'testFiles.txt')
            # testfiles_p = f'{output_dir}/{k}_testFiles.txt'
            v.to_csv(testfiles_p, header=False, index=False, sep='\t')
            dset_readme = f'{k} path: {testfiles_p}\ndatetime: {date}\n'
            testset_res_paths = {}
            for l, model_path in model_paths.items():
                print(f'@REM @echo off', file=f)
                print(f'REM {exe_p}\n', file=f)
                class_dir = os.path.join(model_path, "Classifier_Prod") if 'Classifier_Prod' in os.listdir(model_path) else os.path.join(model_path, "Classifier")
                cli_file = os.path.join(class_dir, 'model_def.cli')
                # cli_file = f'{model_path}\\Classifier_Prod\\model_def.cli'
                # class_dir = f'{model_path}\\Classifier_Prod'
                # test_alias = f'{l}_{k}_{date}'
                test_suff = f'{l}_{date}'
                # rep_name = f'stm_output_{test_alias}.csv'
                rep_name = f'stm_output_{test_suff}.csv'
                # class_rep_name = f'class_output_{test_alias}.csv'
                class_rep_name = f'class_output_{test_suff}.csv'
                # testset_res_paths[l] = os.path.join(output_dir, class_rep_name)
                testset_res_paths[l] = os.path.join(dset_output_dir, class_rep_name)
                dset_readme += f'{l} model: {model_path}\n'
                print(f'{exe_p} ^', file=f)
                print(f'\t--filelist {testfiles_p} ^', file=f)
                print(f'\t--clifile {cli_file} ^', file=f)
                print(f'\t--classifier-directory {class_dir} ^', file=f)
                print(f'\t--report-name {rep_name} ^', file=f)
                print(f'\t--log classifier_taxonomy.log ^', file=f)
                print(f'\t--classifier-report-name {class_rep_name} ^', file=f)
                print(f'\t--use-correct-report-header ^', file=f)
                # print(f'\t--outputdir {output_dir} ^', file=f)
                print(f'\t--outputdir {dset_output_dir} ^', file=f)
                print(f'\t-ma 3', file=f)
                print(f'\n', file=f)
            test_results_paths[k] = testset_res_paths
            readme_p = os.path.join(dset_output_dir, 'readme.txt')
            with open(readme_p, 'w') as f2:
                f2.write(dset_readme)
    print(bat_fp)
    print(test_results_paths)
    return bat_fp, test_results_paths


def split_on_second(s, deliminator):
    parts=s.split(deliminator)
    # return [deliminator.join(parts[:2]) + deliminator, parts[2].strip()]
    return [deliminator.join(parts[:2]), parts[2].strip()]


def apply_prod_clf_logic(l2_l3_results_dict: dict, write_path: str = None):
    l3_clfs = l2_l3_results_dict['l3']
    l2_clfs = l2_l3_results_dict['l2']
    for c in ['Classification', 'SecondClassification', 'Classification3']:
        l2_clfs[c] = l2_clfs[c].str.split(" > ").str[0] + " > " + l2_clfs[c].str.split(" > ").str[1]

    if not len(l3_clfs) == len(l2_clfs):
        logger.info(f'Number of scored interactions not the same in secondary and tertiary outputs. Exiting.')
        return
    # l3_clfs.drop(['Score', 'StatusCode', 'SecondScore'], axis=1, inplace=True)
    # l2_clfs.drop(['Score', 'StatusCode', 'SecondScore'], axis=1, inplace=True)
    class_cols = ['Classification', 'SecondClassification', 'Classification3']

    # System 2 is the tertiary model output classifications. System 1 is the secondary model output classifications
    # There are 3 classifications for each system and 3 levels for each. Label them accordingly
    # E.g. Sys2_Class1_l2 is the secondary classification of the classification 1 from the tertiary model (system 2).
    for i, v in enumerate(class_cols):
        l3_clfs[[f'Sys2_Class{i+1}_l2', f'Sys2_Class{i+1}_l3']] = l3_clfs[v].apply(lambda x: pd.Series(split_on_second(x, " > ")))

    # Combine classifications from secondary and tertiary
    combined = l2_clfs.merge(l3_clfs, how='inner', on='File', suffixes=['_l2', '_l3'])

    # Pick final classifications based on logic rules. This gives preference to secondaries predicted by secondary model over inferred secondaries from the tertiary model
    classes = [1, 2, 3]
    combined['final_c1'] = ""
    combined['final_c2'] = ""
    combined['final_c3'] = ""
    combined['final_c1_l3'] = combined.apply(lambda row: row['Sys2_Class1_l3'] if row['Classification_l2']==row['Sys2_Class1_l2'] 
                                                            else (row['Sys2_Class2_l3'] if row['Classification_l2']==row['Sys2_Class2_l2']
                                                            else (row['Sys2_Class3_l3'] if row['Classification_l2']==row['Sys2_Class3_l2']
                                                            else "Z-Other")), axis=1)
    combined['final_c2_l3'] = combined.apply(lambda row: row['Sys2_Class2_l3'] if row['SecondClassification_l2']==row['Sys2_Class2_l2'] 
                                                            else (row['Sys2_Class3_l3'] if row['SecondClassification_l2']==row['Sys2_Class3_l2']
                                                            else "Z-Other"), axis=1)
    combined['final_c3_l3'] = combined.apply(lambda row: row['Sys2_Class3_l3'] if row['Classification3_l2']==row['Sys2_Class3_l2'] 
                                                            else "Z-Other", axis=1)         
    combined['final_c1'] = combined['Classification_l2'] + ' > ' + combined['final_c1_l3']
    combined['final_c2'] = combined['SecondClassification_l2'] + ' > ' + combined['final_c2_l3']
    combined['final_c3'] = combined['Classification3_l2'] + ' > ' + combined['final_c3_l3']
    combined['InteractionID'] = combined.File.str.split('\\').str[-1].str.split('_').str[1].astype(str)

    # Create final output 
    combined_out = combined[['File', 'final_c1', 'final_c2', 'final_c3']]
    nums = [1, 2, 3]
    levels = ['Primary', 'Secondary', 'Tertiary']
    for num in nums:
        for i, v in enumerate(levels):
            combined_out[f'Complaint Classification {num} {v}'] = combined_out[f'final_c{num}'].str.split(" > ").str[i]
    combined_out.drop(['final_c1', 'final_c2', 'final_c3'], axis=1, inplace=True)

    if write_path:
        combined_out.to_csv(write_path, sep='\t', header=True, index=False)
    return combined_out, combined


def run_multiclass_models_with_logic(data_dict: dict, model_paths: dict, testrun_name: str, output_dir: str):
    l2_l3_bat, results_paths = create_multimodel_bat(data_dict, model_paths, testrun_name, output_dir)
    # results_paths format - {'test_set_name': {'l3': path_to_l3_results, 'l2': path_to_l2_results}}

    run_bat_file(l2_l3_bat)
    # proc = subprocess.run(l2_l3_bat, shell=True)

    # if proc.returncode == 0:
    #     logger.info('Multiclass model run complete.')
    # else:
    #     logger.info('Error with multiclass model run.')
    #     return

    # read in results
    for test_set_name, results_paths_dict in results_paths.items():
        # For each test set, create a dict for the l2 and l3 results. Similar format to results_paths
        test_set_res_dict = {}
        # Format: {'l2': df_with_results, 'l3': df_with_results}
        for level, class_report_path in results_paths_dict.items():
            test_set_res_dict[level] = pd.read_csv(class_report_path, comment="#", header=0, sep='\t')
        # results_dict[test_set_name] = test_set_res_dict
        combined_out_file_p = results_paths_dict["l3"].replace(".csv", "_wlogic.csv")
        print(combined_out_file_p)
        combined_out_caars_marapr25 = apply_prod_clf_logic(test_set_res_dict, combined_out_file_p)
    return combined_out_caars_marapr25


if __name__ == "__main__":
    # Create dictionary for test sets to be run in the form of {'test set name': test_files_list}. 
    # Create a dict even if you are running a single list of files
    # Test files should be a series (single column). The function will write this to a txt file.
    # files_path = "...."
    
    testset_path = r'S:\Nicetech\ForResearch\005_CAARS_Validations\files_CAARS_Sep2025.csv'
    files = pd.read_csv(testset_path, sep='\t').NxprFilePath
    test_alias = 'CAARS_Sept25'
    files_dict = {test_alias: files}

    #testset2_path = r'S:\Nicetech\ForResearch\005_CAARS_Validations\NXPRS_CAARS_validations_JanJun2025.csv'
    #files2 = pd.read_csv(testset2_path).NxprFilePath
    #test_alias2 = 'CAARS_JanJun25' RENAME THIS!!!
    #files_dict[test_alias2] = files2


    # "S:\Nicetech\ForResearch\005_CAARS_Validations\NXPR_CAARS_Sep2025_TruthDatawithFlips.csv"
    # testset_path = r'S:\Nicetech\ForResearch\005_CAARS_Validations\NXPR_CAARS_Oct2025.csv'  # Orig file (above) doesnt work because XLS makes a completely unusable format.  'x2' is a custom-crafted simple list of NxPrs.  Getting truth column (10th) out will take more work...
    # files = pd.read_csv(testset_path).NxprFilePath
    # print(f'found {len(files)} files to process')
    # test_alias = 'CAARS_Oct_2025'
    # files_dict = {test_alias: files}

    # tert_model = r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l3_Sep25_v2'
    # For Jon e.g. sec_model = [r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Oct25]

    ## Jon - run Sept CAARS data (319 files) using L2 model built using production binary models plus multiclass trained on weak-labeled-by-topicai 100k:
    #tert_model = r'N:\NxResearch\Complaints\056_Col_CS_Combined_MulticlassClassifier\data\Tertiary_Classifier_70k'
    #sec_models = [r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Oct25']

    # Jon - run Sept CAARS data (319 files) using Nahum's 1M-trained L3 plus two L2's:
    #  L2 #1 :  
    #  L2 #2 :  
    tert_model = r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\BuildTert1M_Feb2025'
    sec_models = [r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Oct25_v3']

    # sec_models = [r'N:\NxResearch\Complaints\057_Col_CS_Combined_Secondary_MulticlassClassifier\data\Combined_Secondary_Classifier_100K']
    # sec_models = [r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Sep25_v4']
    # sec_models = [
    #     r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Aug25',
    #     r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Aug25_v2',
    #     r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Jul25_v2',
    #     r'S:\Nicetech\060_Col_CS_MulticlassClassifier\data\Build_l2_Sep25',
    #     r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Sep25_v2'  
    # ]

    # truth_p060 = pd.read_csv('N:\\NxResearch\\Complaints\\060_Col_CS_MulticlassClassifier\\data\\BuildSec_Jun25\\TrainingValFiles\\truth_6-26.csv', sep='\t', header=0)
    # test_l2 = truth_p060[truth_p060.DisjointReasonTest]
    build_path = tert_model
    # build_path = r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\BuildSec_Jun25'
    # files_dict = {'junjul24_test_slice': test_l2.Nxpr}
    # test_alias = 'Jun25L2_Feb25L3'

    for sec_model in sec_models:
        test_alias = f'w_{os.path.basename(sec_model)}'
        output_dir = os.path.join(build_path, 'Testing', test_alias)
        test_dt = datetime.now().strftime('%Y-%m-%d %H:%M')

        models = {'l3': tert_model, 'l2': sec_model}
        # test_readme = f'L2: {sec_model}\nL3: {tert_model}\ntest_sets: CHART Mar-Aug 2025. Path: {testset_path}\nCAARS Jan-Jun 2025. Path: {testset2_path}\ndatetime: {test_dt}'
        
        run_multiclass_models_with_logic(files_dict, models, test_alias, output_dir)
        # readme_p = os.path.join(output_dir, 'readme.txt')
        # with open(readme_p, 'w') as f:
        #     f.write(test_readme)


    # These are the models to score
    # tert_model = r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\BuildTert1M_Feb2025'
    # sec_model = r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\BuildSec_Jun25'
    # sec_model = r'N:\NxResearch\Complaints\060_Col_CS_MulticlassClassifier\data\Build_l2_Aug25'
    
    
    
    # models = {'l3': tert_model, 'l2': sec_model}
    # test_readme = f'L2: {sec_model}\nL3: {tert_model}\ntest_set: CHART Mar-Aug 2025. Path: {testset_path}\ndatetime: {test_dt}'

    

