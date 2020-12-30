# NEURO(botics) MANAGER

## neuromanager run (neurun.py)
```
neurun SUPPORT DEVICE SCRIPT FLAGS
```
where support/device information is provided by ```config.json``` which has the following structure
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
```
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

## neuromanager sweep (neusweep.py)
```
neusweep SCRIPT FLAGS
```

