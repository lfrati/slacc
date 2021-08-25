# NEURO(botics) simple job MANAGER

Isn't it fun to have a nice GPU in your computer and to experiment left and right? You just write some python scripts and then launch them on your machine, wait, repeat. Life is simple and beautiful.
But then inevitably it happens. 
You want to launch more scripts, longer scripts, test different parameters... 
So you have to go beg the SLURM gods to assist you.
Evil bash scripts start popping up everywhere, requesting resources, launching jobs....
Wouldn't it be nice to just abstract that pain away and remain in python land?

## [launcher](launcher)
Allows you to turn
```python
python train.py --lr=0.01
```
into
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
It has the following syntax
```
launcher {--runs} CONFIG SCRIPT FLAGS
```
where support/device information needs to be provided by ```config.json``` with the following structure
```
{
  NAME:
    DEVICE 
    HOST
    ENV
    RESOURCES
}
```
where NAME is used to select the specs, DEVICE is either "gpu" or "cpu", HOST is either "local" or a remote server name, ENV specifies how to set up virtual environments if needed and RESOURCES specifies the option to pass to SLURM
e.g.
```json
{
  "local-gpu": {
    "device": "gpu",
    "host": "local",
    "env": "conda activate deep",
    "resources": ""
  },
  "local-cpu": {
    "device": "cpu",
    "host": "local",
    "env": "conda activate deep",
    "resources": ""
  },
  "remote-gpu": {
    "env": "conda activate deep",
    "device": "gpu",
    "host": "sersver-name",
    "resources": {
      "time": "2-00:00:00",
      "account": "lfrati",
      "partition": "big-gpu",
      "cpus-per-task": 1,
      "gres": "gpu:v100:1",
      "mem": "8000"
    }
  },

}
```
The script then launches jobs either directly (if support is local) or through a SLURM sbatch file.
Why also support a local flag? Because it is useful in combination with the --runs flag.
Since the script uses subprocesses to launch the scripts and awaits them before moving to the next we can easily chain multiple long jobs on a local machine with a single GPU.
E.g.
```
launcher --runs=10 local-gpu dummytrain.py --steps=10
```
