import torch
from data_loader import load_dictionary, load_numeric_min_max, load_plans_and_obtain_bounds, prepare_imdb_dataset_for_encoding, prepare_imdb_dataset_for_extraction, load_imdb_dataset
import os
from os import path
from util import EncodeContext

from feature_extraction.extract_features import feature_extractor
from feature_extraction.sample_bitmap import prepare_samples, add_sample_bitmap

from plan_encoding.encode_plan import encode_and_save_job_plans

from training.train_and_test import train_and_test
from training.eval import model_eval

def extract_feature():
    dataset = load_imdb_dataset('./data/imdb_data_csv')
    print('load imdb dataset')
    column2pos, indexes_id, tables_id, columns_id, physic_ops_id, compare_ops_id, bool_ops_id, table_names = prepare_imdb_dataset_for_extraction(dataset)

    feature_extractor('./data/plans.json', './data/plans_seq.json')
    print('extract plan features')

    sample_num = 1000
    sample = prepare_samples(dataset, sample_num, table_names)
    add_sample_bitmap('./data/plans_seq.json', './data/plans_seq_sample.json', dataset, sample, sample_num)
    print('add sample bitmaps')


def encode_plan():
    data_dir = 'data'
    data, tables_id, columns_id, indexes_id, physical_ops_id, compare_ops_id, bool_ops_id = prepare_imdb_dataset_for_encoding(data_dir)
    print('data prepared')
    # YOUR CODE HERE: set the word_vectros_path which is used to encoding strings or just put wordvectors_updated.kv and
    # wordvectors_updated.kv.vectors.npy under data directory.
    word_vectors_path = 'data/wordvectors_updated.kv'
    word_vectors = load_dictionary(word_vectors_path)
    print('word_vectors loaded')
    min_max_values = load_numeric_min_max(path.join(data_dir, 'min_max_vals.json'))
    print('min_max loaded')

    plans, plan_node_max_num, condition_max_num, cost_label_min, cost_label_max, card_label_min, card_label_max = \
        load_plans_and_obtain_bounds(path.join(data_dir, 'plans_seq_sample.json'))
    print('plans loaded')

    ctx = EncodeContext(data, word_vectors, min_max_values, tables_id, columns_id, indexes_id, physical_ops_id,
                        compare_ops_id, bool_ops_id, plan_node_max_num, condition_max_num, cost_label_min,
                        cost_label_max, card_label_min, card_label_max)
    out_dir = path.join('data', 'job')
    os.makedirs(out_dir, exist_ok=True)
    encode_and_save_job_plans(ctx, plans, batch_size=64, out_dir=out_dir)
    print('data encoded')


def train():
    data_dir = 'data'
    data, tables_id, columns_id, indexes_id, physical_ops_id, compare_ops_id, bool_ops_id = prepare_imdb_dataset_for_encoding(data_dir)
    print('data prepared')
    min_max_values = load_numeric_min_max(path.join(data_dir, 'min_max_vals.json'))
    print('min_max loaded')

    plans, plan_node_max_num, condition_max_num, cost_label_min, cost_label_max, card_label_min, card_label_max = \
        load_plans_and_obtain_bounds(path.join(data_dir, 'plans_seq_sample.json'))
    print('plans loaded')

    ctx = EncodeContext(data, None, min_max_values, tables_id, columns_id, indexes_id, physical_ops_id,
                        compare_ops_id, bool_ops_id, plan_node_max_num, condition_max_num, cost_label_min,
                        cost_label_max, card_label_min, card_label_max)
    model = train_and_test(ctx, 0, 20, 20, 22, 10, path.join('data', 'job'))
    print("finish training")
    torch.save(model, path.join(data_dir, 'model'))
    print("finish")


def eval():    
    data_dir = 'data'
    data, tables_id, columns_id, indexes_id, physical_ops_id, compare_ops_id, bool_ops_id = prepare_imdb_dataset_for_encoding(data_dir)
    print('data prepared')
    min_max_values = load_numeric_min_max(path.join(data_dir, 'min_max_vals.json'))
    print('min_max loaded')

    plans, plan_node_max_num, condition_max_num, cost_label_min, cost_label_max, card_label_min, card_label_max = \
        load_plans_and_obtain_bounds(path.join(data_dir, 'plans_seq_sample.json'))
    print('plans loaded')

    ctx = EncodeContext(data, None, min_max_values, tables_id, columns_id, indexes_id, physical_ops_id,
                        compare_ops_id, bool_ops_id, plan_node_max_num, condition_max_num, cost_label_min,
                        cost_label_max, card_label_min, card_label_max)
    model = torch.load(path.join(data_dir, 'model'))
    model_eval(ctx, model, 22, 25)


if __name__ == '__main__':
    # Extract features from plans and add sample bitmaps.
    # plans.json -> plans_seq.json -> plans_seq_sample.json
    extract_feature()
    # Encode plan features and dump them into disk in batches.
    # There are 1600 plans and batch_size = 64, so there are 1600 / 64 = 25 batches.
    # Inputs and outputs of each batch are written into files in data/job directory as follows:
    # target_cost_xxx.np, target_cardinality_xxx.np, operators_xxx.np, extra_infos_xxx.np,
    # condition1s_xxx.np, condition2s_xxx.np, samples_xxx.np, condition_masks_xxx.np, mapping_xxx.np
    # We read inputs and outputs of each batch when training, validating and testing the model.
    encode_plan()
    # Use batch 0-19 for train and 20-21 for validation. After finish training, save the model.
    train()
    # Load the model and use batch 22-24 for evaluation. It generates cardinality.png, cost.png and results.json.
    eval()


