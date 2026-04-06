# Robocept Bringup (System) — TODO

## URDF / Robot Model
- [ ] Update chassis dimensions in URDF once actual robot is purchased
- [ ] Update wheel radius, separation, and count to match real robot
- [ ] Measure and update LiDAR mount position (`base_to_lidar` joint)
- [ ] Measure and update camera mount position (`base_to_camera` joint)
- [ ] Add visual meshes (STL/DAE) for a realistic model (optional, cosmetic)

## Simulation (Gazebo)
- [ ] Install Gazebo on development machine: `sudo apt install ros-${ROS_DISTRO}-gazebo-ros-pkgs`
- [ ] Test `ros2 launch robocept_system sim.launch.py` — verify robot spawns and sensors publish
- [ ] Test teleop in simulation: `ros2 run teleop_twist_keyboard teleop_twist_keyboard`
- [ ] Verify simulated LiDAR scan on `/robocept/lidar/scan`
- [ ] Verify simulated camera on `/robocept/camera/color/image_raw`
- [ ] Test obstacle avoidance in simulation
- [ ] Create additional test worlds (open field, maze, cluttered room)

## Static Transforms
- [ ] Update `config/static_transforms.yaml` with real sensor mounting positions
- [ ] Once URDF is finalized, remove static_transforms.yaml and use robot_state_publisher only

## System Integration
- [ ] Test full stack launch: `ros2 launch robocept_system robot.launch.py` on real hardware
- [ ] Add systemd service files for auto-start on boot
- [ ] Add a launch file that includes AI inference node
- [ ] Configure network for remote monitoring (RViz on laptop, robot on Jetson)

## Workspace Setup
- [ ] Document full workspace setup in README:
  ```
  mkdir -p ~/robocept_ws/src && cd ~/robocept_ws/src
  git clone all 5 repos
  cd .. && colcon build --symlink-install
  ```
- [ ] Create a `robocept.repos` file for `vcs import` to clone all repos at once
