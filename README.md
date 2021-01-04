# NEURO(botics) simple job MANAGER

Isn't it fun to have a nice GPU in your computer and to experiment left and right with neural networks? You just write some python scripts and then launch them on your machine, wait, repeat. Life is simple and beautiful.
But then inevitably it happens. You want to launch more scripts, longer scripts, test different parameters... So you have to go beg the SLURM gods to assist you.
Evil bash scripts start popping up everywhere, requesting resources, launching jobs....
Wouldn't it be nice to just abstract that pain away and remain in python land?

There are two major functionalities that we need to launch scripts:
1. something that turns python train.py into a slurm-able job
2. something that turns some parameters options in many job scripts

## neuromanager run (neurun.py)
The first piece of the puzzle is `neurun.py` which is in charge of turning
```python
python dummytrain.py --lr=0.01
```
into:
```bash
#!/bin/bash
#SBATCH --time=2-00:00:00
#SBATCH --account=myproject
#SBATCH --partition=big-gpu
#SBATCH --gres=gpu:p100:1
#SBATCH --mem=8000

source activate deep
python dummytrain.py --lr=0.01
```
It has the following syntax
```
neurun {--runs} SUPPORT DEVICE SCRIPT FLAGS
```
where support/device information needs to be provided by ```config.json``` with the following structure
```
{
  local: (support) {
    CPU: (device) {"env": ... , "resources": ...}
    GPU: (device) {"env": ... , "resources": ...}
  },
  slurm: (support) {
    CPU: (device) {"env": ... , "resources": ...}
    GPU: (device) {"env": ... , "resources": ...}
  }
}
```
e.g.
```json
{
  "local": {
    "cpu": { "env": "conda activate deep", "resources": "" },
    "gpu": { "env": "conda activate deep", "resources": "" }
  },
  "slurm": {
    "gpu": {
      "env": "source activate deep",
      "resources": {
        "time": "2-00:00:00",
        "account": "myproject",
        "partition": "big-gpu",
        "gres": "gpu:p100:1",
        "mem": "8000"
      }
    },
    "cpu": {
      "env": "source activate deep",
      "resources": {
        "time": "4-00:00:00",
        "account": "myproject",
        "partition": "big-mem",
        "mem": "16000"
      }
    }
  }
}
```
The script then launches the required script either directly (if support is local) or through a SLURM sbatch file.
Why also support a local flag? Because it is useful in combination with the --runs flag.
Since the script uses subprocesses to launch the scripts and awaits them before moving to the next we can easily chain multiple long jobs on a local machine with a single GPU.
E.g.
```
neurun.py --runs=10 local gpu dummytrain.py --steps=10
```

## neuromanager sweep (neusweep.py)
Now that we have a simple way to make our scripts SLURM friendly we need to find a way to launch a lot of them.
For this task we can use `neusweep.py` with the following syntax
```
neusweep CMD
```
The script looks for a file `params.json` that contains the parameters to sweep over
```
{ "parameter name":[list of valules] }
```
e.g.
```json
{
  "lr": [0.1, 0.001],
  "layers": [4,8,16]
}
```
The script then generates all possible combinations and passes them to the CMD. Flags that don't need sweeping over can be passed directly to the inner CMD.
E.g.
```
python neusweep.py dummytrain.py --steps=100
```
reads the example `params.json` mentioned above and launches
```
python dummytrain.py --steps=100 --lr=0.1 --layers=4
python dummytrain.py --steps=100 --lr=0.1 --layers=8
python dummytrain.py --steps=100 --lr=0.1 --layers=16
python dummytrain.py --steps=100 --lr=0.01 --layers=4
python dummytrain.py --steps=100 --lr=0.01 --layers=8
python dummytrain.py --steps=100 --lr=0.01 --layers=16
```

Given their Unix-like piping nature we can then combine `neusweep` and `neurun` to launch a ton of experiments on a job scheduler using

```
python neusweep.py neurun.py --runs=10 slurm gpu dummytrain.py --steps=10
                   
```
