import argparse
import random as rnd

import torch

import model.modelfactory as mf
import utils.utils as utils
import wandb
from datasets.OmniSampler import OmniSampler
from experiment.experiment import experiment
from experiment.writer import Writer
from model.meta_learner import MetaLearingClassification


def main(args):

    utils.set_seed(args.seed)
    args.model_name = args.model_type

    # DATA & MODEL SETUP

    omni_sampler = OmniSampler(root="../data/omni")

    # -----------------------------------------------------------------
    #      model          rln   outer (meta)      inner (standard)
    # -----------------------------------------------------------------
    # ANML                 14   NM + P            P
    # OML                  24   RLN + P           P
    # hebb                 12   RLN + hebb        hebb
    # hebb_OML             24   RLN + hebb        hebb
    # diffplast            25   RLN + hebb + P    P + hebb
    # neuromod_diffplast   14   NM + P + hebb     P + hebb
    # neuromod_hebb        14   NM + P + hebb     P + hebb
    # small_OML            12   RLN + P           P
    # small_hebb            8   RLN + hebb        hebb
    # -----------------------------------------------------------------
    # RLN meaning:
    # The rln depth determines what is allowed to update in the inner loop.
    # Layers < rln -> .learn = False -> inner frozen  - outer updated
    # Layers > rln -> .learn = True  -> inner updated - outer updated
    # i.e.
    # 0  := everything is trained in the inner loop, AND the outer loop
    # 99 := nothing is trained in the inner loop, only in the outer loop

    if args.rln < 0:
        rlns_per_treatment = {
            "ANML": 14,
            "OML": 24,
            "hebb": 12,
            "hebb_OML": 24,
            "diffplast": 25,
            "neuromod_diffplast": 14,
            "neuromod_hebb": 14,
            "small_OML": 12,
            "small_hebb": 8,
        }
        args.rln = rlns_per_treatment[args.model_type]

    # When greedy I train everything everytime -> rln = 0
    if args.greedy == 1:
        args.model_name = "greedy_" + args.model_name
        args.rln = 0

    else:

        # The noinner flag disables inner loop update
        if args.noinner == 1:
            args.model_name = "noinner_" + args.model_name

        # The nometa flag disables outer loop update
        if args.nometa == 1:
            args.model_name = "nometa_" + args.model_name

    config = mf.ModelFactory.get_model(args.model_type)

    if args.device == "gpu" and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    model = MetaLearingClassification(args, config).to(device)

    # Set the .learn field to False for those weight that will be updated in the outer loop only
    utils.freeze_layers(args.rln, model, phase="training")
    hebb = torch.zeros((1000, 2304)).to(device)

    # LOGGING SETUP

    my_experiment = experiment(args.project, args, "../results/")
    logger = my_experiment.logger
    writer = Writer(
        path=my_experiment.path,
        fieldnames=["it", "acc", "loss", "train_acc", "task_added", "test_tasks"],
    )
    # Logging these before wandb.init so I have a log if the init fails... it happened...
    logger.info(config)
    logger.info(args)
    wandb_opts = {
        "project": args.project,
        "group": f"{args.model_name}-{utils.hash_args(args)}",
        "job_type": "train",
        "config": vars(args),
    }
    logger.info(wandb_opts)
    wandb.init(**wandb_opts)

    # store dir to save stuff (args is passed to all inner classes, God have mercy.)
    args.dir = my_experiment.dir
    logger.info(args.dir)

    for step in range(args.steps):
        args.step = step

        if args.hebb_reset == 1:
            # Create fresh hebbian component, this prevents learning about anything apart from the current task
            hebb = torch.zeros((1000, 2304)).to(device)
            # nn.init.kaiming_normal_(hebb)

        (x_spt, y_spt), (x_qry, y_qry) = (
            omni_sampler.sample_train(),
            omni_sampler.sample_valid(),
        )
        x_qry, y_qry = torch.cat([x_qry, x_spt]), torch.cat([y_qry, y_spt])

        y_spt = y_spt.unsqueeze(1)
        y_qry = y_qry.unsqueeze(1)

        # x_spt -> [examples (e.g. 20), 1, 3, 28, 28] images
        # y_spt -> [examples (e.g. 20), 1] ground truth classes
        # x_qry -> [1, Learn + Remember (e.g. 84 = 64 + 20), 3, 28, 28] images, why the 1 in front?
        # y_qry -> [1, Learn + Remember (e.g. 84 = 64 + 20)] ground truth classes

        x_spt, y_spt, x_qry, y_qry = (
            x_spt.to(device),
            y_spt.to(device),
            x_qry.to(device),
            y_qry.to(device),
        )

        if args.train_reset:
            # all tasks in y_spt are the same, I'll just check the first
            curr_task = y_spt.flatten()[0]
            hebb = model.reset_classifer(curr_task, hebb)

        accs, post_train_accs, loss, hebb = model(x_spt, y_spt, x_qry, y_qry, hebb)

        # Logging results and checkpoints  ##########

        wandb.log(
            {"acc": accs, "loss": loss.item(), "train_acc": post_train_accs}, step=step
        )

        writer.add(
            {
                "it": step,
                "acc": accs,
                "loss": loss.item(),
                "train_acc": post_train_accs,
                "task_added": y_spt[0].item(),  # all y_spt values are the same
                "test_tasks": list(set(y_qry.flatten().tolist())),
            }
        )

        if step % 10 == 0:
            tests = len(y_qry.flatten())
            logger.info(
                f"step: {step} \t training acc {accs} ({int(accs * tests)}/{tests})"
            )
        if step % 100 == 0:
            # writing to file on teton seems suuuuuuuper slow, let's try to keep it to a minimum
            writer.write()
            # torch.save(maml.net,my_experiment.save_dir + f"{args.model_type}_{step:06d}.model")
            # torch.save(hebb, my_experiment.save_dir + f"{args.model_type}_{step:06d}.hebb")
        if step % 1000 == 0:
            torch.save(
                model.net,
                my_experiment.save_dir / f"{args.model_type}-{step:06d}.model",
            )
            # if "hebb" in args.model_type:
            #     torch.save(
            #         hebb, my_experiment.save_dir / f"{args.model_type}-{step:06d}.hebb"
            #     )

    # store last results
    writer.write()
    # to record execution time and commit
    my_experiment.finish()

    # save final model and hebb
    torch.save(
        model.net, my_experiment.save_dir / f"{args.model_type}-{step:06d}.model"
    )
    # if "hebb" in args.model_type:
    #     torch.save(hebb, my_experiment.save_dir / f"{args.model_type}-{step:06d}.hebb")


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--steps",
        type=int,
        help="How many outer loop iterations (a.k.a. epochs)",
        default=20000,
    )
    argparser.add_argument(
        "--seed",
        type=int,
        help="Seed to initialize pseudo-random generators",
        default=rnd.randint(1, 10000),
    )
    argparser.add_argument(
        "--meta_lr",
        type=float,
        help="What meta-level outer learning rate to use.",
        default=1e-3,
    )
    argparser.add_argument(
        "--update_lr",
        type=float,
        help="task-level inner update learning rate",
        default=1e-1,
    )
    argparser.add_argument(
        "--update_step",
        type=int,
        help="How many task-level inner update steps",
        default=20,
    )
    argparser.add_argument(
        "--dataset",
        help="Name of the dataset to be used. Possible values [omniglot, CIFAR (not implemented)]",
        default="omniglot",
    )
    argparser.add_argument(
        "--hebb_reset",
        help="1: reset hebbian at every inner iteration, 0: no reset.",
        type=int,
        default=0,
    )
    argparser.add_argument(
        "--onehot_lr",
        help="learning rate to use with the onehot target",
        type=float,
        default=1,
    )
    argparser.add_argument(
        "--signvec_lr",
        help="learning rate to use with the signvec target",
        type=float,
        default=1e-2,
    )
    argparser.add_argument(
        "--covrule_lr",
        help="learning rate to use with the covrule target",
        type=float,
        default=1e-2,
    )
    argparser.add_argument(
        "--targ_update_style",
        help="How to deal with predictions/targets. Possible values [keep, diffp, teacher]",
        type=str,
        default="teacher",
    )
    argparser.add_argument(
        "--hebb_targ",
        help="What kind of target to use. Possible values [onehot, signvec, covrule]",
        type=str,
        default="onehot",
    )
    argparser.add_argument(
        "--train_reset",
        help="Control if connections related to class to be trained are reset before meta-train-train",
        type=int,
        default=1,
    )
    argparser.add_argument(
        "--device",
        type=str,
        help="What device to use. Possible values [cpu,gpu]",
        default="gpu",
    )
    argparser.add_argument(
        "--rln", help="Controls how many layers to meta-train", type=int, default=-1
    )
    argparser.add_argument(
        "--noinner", help="Enable/disable inner loop update", type=int, default=0,
    )
    argparser.add_argument(
        "--nometa", help="Enable/disable outer loop update", type=int, default=0,
    )
    argparser.add_argument(
        "--greedy",
        help="Update all the parameters during inner and outer",
        type=int,
        default=0,
    )

    # NEEDED
    argparser.add_argument(
        "--model_type", type=str, help="MRCL, neuromod, neuromod_hebb, hebb"
    )
    argparser.add_argument("--project", help="Name of experiment")

    # argparser.add_argument("--rln", type=int, default=9) # using specific values depending on model
    # argparser.add_argument("--model", type=str, help="epoch number", default="none")
    params = argparser.parse_args()
    print(params)
    main(params)
