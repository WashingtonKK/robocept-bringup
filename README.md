# Robocept Bringup — Top-Level Robot Composition

Top-level ROS 2 workspace that composes all robocept subsystems into a complete robot. This is the single entry point for launching the full robot stack.

## Subsystem Repos

| Repo | Purpose | Interface |
|---|---|---|
| [robocept](https://github.com/WashingtonKK/robocept) | Perception (LiDAR + camera + health) | Publishes `/robocept/*` sensor topics |
| [robocept-control](https://github.com/WashingtonKK/robocept-control) | Motor driver + diff-drive controller | Subscribes `/cmd_vel`, publishes `/odom` |
| [robocept-nav](https://github.com/WashingtonKK/robocept-nav) | Planning + obstacle avoidance | Subscribes sensors, publishes `/cmd_vel` |

## What This Repo Contains

- **URDF/xacro** — full robot model with sensor mounting transforms
- **Top-level launch files** — compose perception + control + nav
- **Static TF** — base_link to sensor frames (until URDF is complete)
- **System configs** — deployment-specific settings

## Frame Tree

```
odom
 └── base_link                    (from robocept-control /odom TF)
      ├── robocept_lidar_frame    (static TF from this repo)
      └── camera_link             (static TF from this repo)
           ├── camera_color_optical_frame
           ├── camera_depth_optical_frame
           └── ...                (from realsense2_camera)
```

## Workspace Setup

Clone all repos into a single colcon workspace:

```bash
mkdir -p ~/robocept_ws/src
cd ~/robocept_ws/src

git clone https://github.com/WashingtonKK/robocept.git
git clone https://github.com/WashingtonKK/robocept-control.git
git clone https://github.com/WashingtonKK/robocept-bringup.git
```

## Build

```bash
cd ~/robocept_ws
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Usage

```bash
# Full robot (perception + control + static TF)
ros2 launch robocept_system robot.launch.py

# Headless Gazebo Sim only
ros2 launch robocept_system sim.launch.py headless:=true

# Headless Gazebo Sim + obstacle avoidance + sim health monitor
ros2 launch robocept_system sim_obstacle.launch.py headless:=true

# Safe teleop into the obstacle avoider (run in a second terminal)
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args --remap cmd_vel:=/nav_cmd_vel

# Perception only (sensor testing, no motors)
ros2 launch robocept_bringup perception.launch.py

# Control only (motor testing with teleop, no sensors)
ros2 launch robocept_base base.launch.py

# Teleop (keyboard control)
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

## Configuration

### Sensor Mounting (MUST configure for your robot)

Edit `src/robocept_system/config/static_transforms.yaml` with the physical sensor positions on your robot chassis:

- `base_to_lidar`: XYZ offset + RPY rotation from base_link to LiDAR
- `base_to_camera`: XYZ offset + RPY rotation from base_link to camera

### Adding ML Models

Place models in a dedicated ROS 2 package (e.g., `robocept_ai`):

```
robocept_ws/src/
  robocept_ai/
    models/           ← .onnx, .tflite, .pt files
    robocept_ai/
      detector.py     ← inference node
    launch/
      inference.launch.py
```

The AI node subscribes to perception topics (`/robocept/camera/color/image_raw`) and publishes detections. It does NOT go inside robocept or robocept-control.

## Where Does Each Logic Live?

| Logic | Repo | Why |
|---|---|---|
| Sensor drivers + health | `robocept` | Perception is self-contained |
| Motor commands + odometry | `robocept-control` | Hardware-specific, independent testing |
| Obstacle avoidance / planning | `robocept-nav` (future) | Consumes sensors, produces /cmd_vel |
| ML inference (detection, etc.) | `robocept_ai` (future) | Heavy deps (torch, onnx), independent release |
| URDF + system composition | `robocept-bringup` (this repo) | Glue layer, robot-specific |
