# NEURO(botics) simple job MANAGER

Isn't it fun to have a nice GPU in your computer and to experiment left and right? You just write some python scripts
and then launch them on your machine, wait, repeat. Life is simple and beautiful.

But then inevitably it happens. You want to launch more scripts, longer scripts, test different parameters... 

So you have to go beg the SLURM gods to assist you. Evil bash scripts start popping up everywhere, requesting resources, launching jobs....

Wouldn't it be nice to just abstract that pain away and remain in python land?

## Prerequisites

- Python >=3.5 
- PyTorch >=1.6.0
- psutil
- pynvml

Most of these utilities are only needed if you want to run `gpu_check.py`.

To set up a compatible conda environment:
```shell
$  conda create -n <env-name> -c conda-forge -c pytorch python=3.9 psutil pynvml pytorch cudatoolkit=10.2
```
You may want to check [here](https://pytorch.org/get-started/locally/) to confirm the pytorch installation procedure is
correct for your GPU and NVIDIA driver.

We also recommend that you add the `neuromanager/` folder to your `PATH`, so you can call these tools easily from the
command line.
```shell
export PATH=$HOME/scratch/neuromanager:$PATH  # ... or wherever your neuromanager repo lives
```

## [launcher](launcher)

This is a wrapper around `sbatch` to make it way easier to launch python scripts quickly. It allows you to turn:
```shell
python train.py --lr=0.01
```
into something like:
```bash
#!/bin/bash
#SBATCH --time=2-00:00:00
#SBATCH --account=myproject
#SBATCH --partition=big-gpu
#SBATCH --gres=gpu:p100:1
#SBATCH --mem=8000

conda activate deep
python train.py --lr=0.01
```
Even better, it makes it easy to launch parameter sweeps as a job array.

### Basic Usage

It has the following syntax:
```
launcher [-h] [--runs RUNS] [--argfile ARGFILE] [-d RUNDIR] [-f] RESOURCE SCRIPT [FLAGS...]
```
where `RESOURCE` is the name of an entry in `config.json` (see [Resource Configurations](#resource-configurations)).

For example, this:
```shell
launcher moran-gpu --runs 2 dummy_gpujob.py --epochs=10 --seed 42
```
is equivalent to twice running this:
```shell
python dummy_gpujob.py --epochs=10 --seed 42
```

Furthermore, any settings accepted by `sbatch` may be supplied on the command line. These will override the options
provided by `config.json`, if given. For example, to add more memory to an existing config:
```
launcher dggpu --mem=64G dummy_gpujob.py
```
**NOTE:** The `sbatch` options must be supplied in `--name=value` fashion, with an
equals sign; `--name value` will *not* parse correctly. For any other options
(including script flags) you may use either format.

### Run Directory

A recommended way to run jobs is to isolate different experiments to separate folders, so that all the related inputs
and outputs can be stored in one place. This can be done with the `-d/--rundir` option:
```shell
launcher dggpu -d experiments/my-next-breakthrough train.py --config train-config.yml
```
In this example, all experiments are stored in the corresponding repository, under the `experiments/` folder. The script
runs in this folder, where it expects to find a `train-config.yml` file. Say the script also generates a
`trained_models/` folder. After running, the experiment folder will contain:
```
__ experiments/my-next-breakthrough/
  |__ train-config.yml
  |__ slurm-12345678.out
  |__ trained_models/
     |__ model-1000.pth
     |__ model-2000.pth
     |__ ...
```

### Running Job Arrays

`launcher` can also run a full sweep of jobs as a single job array.

> :warning: **Careful with program outputs when using this method!**
> For instance, if you are running a program that outputs trained models, you will need to supply each run with a
> separate output folder so they don't overwrite each other.

You can run the same exact job N times via `-r/--runs`:
```shell
launcher bdgpu --runs 10 eval.py --lr 0.01 --num-steps 10 --plots
```

Or you can run a sweep over different configurations, by providing each configuration as a separate line in an
"argfile":
```shell
launcher bdgpu --argfile sweep-args.txt eval.py --plots
```
Where the argfile looks something like this:
```
--lr 0.1  --num-steps 10 -o outfile1
--lr 0.1  --num-steps 15 -o outfile2
--lr 0.03 --num-steps 10 -o outfile3
--lr 0.03 --num-steps 15 -o outfile4
--lr 0.01 --num-steps 10 -o outfile5
--lr 0.01 --num-steps 15 -o outfile6
```

In both cases, these will be launched as a [job array](https://slurm.schedmd.com/job_array.html), making it easier to
track and manage the jobs as a single unit.

## [interact](interact)

This is a wrapper around `srun`. It allows you to easily start an interactive shell on one of the SLURM nodes.  The
shell you launch will be granted the resources of the [resource config]((#resource-configurations)) you provide.

Example:
```shell
interact bdgpu
```

## [Resource Configurations](config.json)

The `config.json` file provides a list of pre-defined resource configurations which the user can use to launch their
SLURM jobs. This is helpful to save sets of `sbatch` or `srun` options that the user uses frequently.

Each entry has the following structure:
```json
{
  NAME:
    DEVICE 
    HOST
    ENV
    RESOURCES
}
```

- `NAME`: a unique identifier for the config.
- `DEVICE`: either "gpu" or "cpu".
- `HOST`: either "local" or a remote server name.
- `ENV`: specifies how to set up virtual environments, if needed.
- `RESOURCES`: specifies the options to pass to SLURM.

Here is a concrete example:
```json
{
  "remote-gpu": {
    "env": "conda activate deep",
    "device": "gpu",
    "host": "server-name",
    "resources": {
      "time": "2-00:00:00",
      "account": "lfrati",
      "partition": "big-gpu",
      "cpus-per-task": 1,
      "gres": "gpu:v100:1",
      "mem": "8000"
    }
  }
}
```

More examples can be found in the [config.json](config.json).
