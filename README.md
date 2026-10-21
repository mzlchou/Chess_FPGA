# Autonomous robotic chess

Senior capstone: a robot that plays chess, with the model running on a custom FPGA accelerator on the AMD Kria KR260.

## Layout

| Folder | What | Owner |
| --- | --- | --- |
| `accelerator/` | FPGA accelerator RTL, Vivado project script, ARM-side driver, baselines | Michael, Hoang, maybe Paul lol |
| `model/` | Model training, quantization, NumPy reference | Matthew |
| `engine/` | Game logic, board sensing, calls the accelerator for a move | TBD |
| `robotics/` | Gantry and motor control | Robotics team |
| `docs/` | System-level docs that span subsystems | Everyone |


## Rules

- Stay in ur own folder
