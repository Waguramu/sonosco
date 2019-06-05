import fnmatch
import io
import os
import logging
import torch.distributed as dist
import sonosco.common.audio_tools as audio_tools

from tqdm import tqdm

import pdb; pdb.set_trace()
logger = logging.getLogger(__name__)


def create_manifest(data_path, output_path, min_duration=None, max_duration=None):
    logger.info(f"Creating a manifest for path: {data_path}")
    file_paths = [os.path.join(dirpath, f)
                  for dirpath, dirnames, files in os.walk(data_path)
                  for f in fnmatch.filter(files, '*.wav')]
    logger.info(f"Found {len(file_paths)} .wav files")
    file_paths = order_and_prune_files(file_paths, min_duration, max_duration)
    with io.FileIO(output_path, "w") as file:
        for wav_path in tqdm(file_paths, total=len(file_paths)):
            transcript_path = wav_path.replace('/wav/', '/txt/').replace('.wav', '.txt')
            sample = f"{os.path.abspath(wav_path)},{os.path.abspath(transcript_path)}\n"
            file.write(sample.encode('utf-8'))


def order_and_prune_files(file_paths, min_duration, max_duration):
    logger.info("Sorting manifests...")
    path_and_duration = [(path, audio_tools.get_duration(path)) for path in file_paths]

    if min_duration and max_duration:
        logger.info(f"Pruning manifests between {min_duration} and {max_duration} seconds")
        path_and_duration = [(path, duration) for path, duration in path_and_duration
                             if min_duration <= duration <= max_duration]

    path_and_duration.sort(key=lambda e: e[1])
    return [x[0] for x in path_and_duration]


def reduce_tensor(tensor, world_size):
    rt = tensor.clone()
    dist.all_reduce(rt, op=dist.reduce_op.SUM)
    rt /= world_size
    return rt
