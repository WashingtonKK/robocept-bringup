# ============================================================================
# Robocept — Master Makefile
# ============================================================================
#
# Convention:
#   make <env>.<action>.<target>
#
#   env:    dev  = simulation / local testing
#           prod = real hardware on Jetson
#
#   action: build, run, test, stop, clean, capture, info
#
#   target: sim, teleop, nav, obstacle, perception, all, etc.
#
# Prerequisites:
#   - ROS 2 Humble sourced:  source /opt/ros/humble/setup.bash
#   - Workspace built:       make dev.build.all
#   - Workspace sourced:     source ~/robocept_ws/install/setup.bash
#
# Quick start:
#   make dev.build.all        # build everything
#   make dev.run.sim          # launch simulation
#   make dev.run.teleop       # drive with keyboard (new terminal)
#   make dev.run.obstacle     # obstacle avoidance (new terminal)
#   make dev.test.obstacle    # automated obstacle avoidance test
#   make dev.stop.all         # kill everything
#
# ============================================================================

SHELL := /bin/bash

# Workspace paths
WS_DIR    := $(HOME)/robocept_ws
SRC_DIR   := $(WS_DIR)/src
BUILD_DIR := $(WS_DIR)/build
LOG_DIR   := /tmp/robocept_logs

# Source both ROS and workspace
SOURCE := source /opt/ros/humble/setup.bash && \
          (test -f $(WS_DIR)/install/setup.bash && source $(WS_DIR)/install/setup.bash || true)

# Ensure log directory exists
$(shell mkdir -p $(LOG_DIR))

# ============================================================================
# BUILD
# ============================================================================

## Build all packages in the workspace
dev.build.all:
	@echo "=== Building all packages ==="
	@cd $(WS_DIR) && $(SOURCE) && colcon build --symlink-install
	@echo "Done. Run: source $(WS_DIR)/install/setup.bash"

## Build only a specific package (usage: make dev.build.pkg PKG=robocept_nav)
dev.build.pkg:
	@echo "=== Building $(PKG) ==="
	@cd $(WS_DIR) && $(SOURCE) && colcon build --symlink-install --packages-select $(PKG)

## Build simulation packages only
dev.build.sim:
	@echo "=== Building simulation packages ==="
	@cd $(WS_DIR) && $(SOURCE) && colcon build --symlink-install \
		--packages-select robocept_msgs robocept_health robocept_system

## Build navigation packages only
dev.build.nav:
	@echo "=== Building navigation packages ==="
	@cd $(WS_DIR) && $(SOURCE) && colcon build --symlink-install \
		--packages-select robocept_nav

# ============================================================================
# DEV — SIMULATION
# ============================================================================

## Launch Ignition Gazebo simulation (headless — no GUI)
dev.run.sim:
	@echo "=== Launching simulation (headless) ==="
	@echo "  Log: $(LOG_DIR)/sim.log"
	@echo "  Stop: make dev.stop.sim"
	@$(SOURCE) && ros2 launch robocept_system sim.launch.py headless:=true 2>&1 | tee $(LOG_DIR)/sim.log

## Launch simulation with Ignition GUI (requires display connected)
dev.run.sim.gui:
	@echo "=== Launching simulation (with GUI) ==="
	@echo "  Requires display connected to Jetson"
	@echo "  Log: $(LOG_DIR)/sim.log"
	@$(SOURCE) && ros2 launch robocept_system sim.launch.py headless:=false 2>&1 | tee $(LOG_DIR)/sim.log

## Launch simulation in background
dev.run.sim.bg:
	@echo "=== Launching simulation in background ==="
	@$(SOURCE) && ros2 launch robocept_system sim.launch.py headless:=true \
		> $(LOG_DIR)/sim.log 2>&1 &
	@echo "PID: $$!"
	@echo "Log: $(LOG_DIR)/sim.log"
	@echo "Stop: make dev.stop.sim"

## Drive robot with keyboard (run in separate terminal while sim is running)
dev.run.teleop:
	@echo "=== Keyboard Teleop ==="
	@echo "  Controls: i=forward, j=left, l=right, k=stop, ,=backward"
	@echo "  Requires: make dev.run.sim (in another terminal)"
	@$(SOURCE) && ros2 run teleop_twist_keyboard teleop_twist_keyboard

## Drive through obstacle avoider (teleop → obstacle_avoider → cmd_vel)
dev.run.teleop.safe:
	@echo "=== Safe Teleop (through obstacle avoider) ==="
	@echo "  Requires: make dev.run.sim + make dev.run.obstacle (in other terminals)"
	@echo "  Teleop publishes to /nav_cmd_vel, obstacle avoider filters to /cmd_vel"
	@$(SOURCE) && ros2 run teleop_twist_keyboard teleop_twist_keyboard \
		--ros-args --remap cmd_vel:=/nav_cmd_vel

# ============================================================================
# DEV — OBSTACLE AVOIDANCE
# ============================================================================

## Launch obstacle avoider node (run while sim is active)
dev.run.obstacle:
	@echo "=== Obstacle Avoider ==="
	@echo "  Subscribes: /robocept/lidar/scan + /nav_cmd_vel"
	@echo "  Publishes:  /cmd_vel (safe velocity)"
	@echo "  Log: $(LOG_DIR)/obstacle.log"
	@$(SOURCE) && ros2 run robocept_nav obstacle_avoider \
		--ros-args \
		-p min_obstacle_distance:=0.35 \
		-p slowdown_distance:=0.8 \
		-p scan_angle_front_deg:=60.0 \
		2>&1 | tee $(LOG_DIR)/obstacle.log

## Launch full nav stack (obstacle avoider + waypoint nav)
dev.run.nav:
	@echo "=== Full Navigation Stack ==="
	@$(SOURCE) && ros2 launch robocept_nav nav.launch.py 2>&1 | tee $(LOG_DIR)/nav.log

## Automated obstacle avoidance test: drive toward wall, verify stop
dev.test.obstacle:
	@echo "=== Obstacle Avoidance Test ==="
	@echo "  1. Sim must be running (make dev.run.sim)"
	@echo "  2. Obstacle avoider must be running (make dev.run.obstacle)"
	@echo "  3. This test sends velocity commands and checks behavior"
	@$(SOURCE) && python3 $(SRC_DIR)/robocept_system/test/test_obstacle_avoidance_sim.py

## Unit tests for obstacle avoidance logic (no sim needed)
dev.test.obstacle.unit:
	@echo "=== Obstacle Avoidance Unit Tests ==="
	@cd $(WS_DIR) && $(SOURCE) && \
		python3 -m pytest $(SRC_DIR)/robocept_nav/test/test_obstacle_logic.py -v

# ============================================================================
# DEV — NAVIGATION
# ============================================================================

## Send a waypoint goal (usage: make dev.nav.goto X=1.0 Y=0.5)
dev.nav.goto:
	@echo "=== Sending waypoint: ($(X), $(Y)) ==="
	@$(SOURCE) && ros2 topic pub /nav_cmd_vel geometry_msgs/msg/Twist \
		"{linear: {x: 0.3}}" --once

## Stop navigation
dev.nav.stop:
	@echo "=== Stopping navigation ==="
	@$(SOURCE) && ros2 service call /robocept/nav/stop std_srvs/srv/Empty

# ============================================================================
# DEV — MONITORING & DIAGNOSTICS
# ============================================================================

## Show all active ROS 2 topics
dev.info.topics:
	@$(SOURCE) && ros2 topic list

## Show topic publish rates
dev.info.hz:
	@echo "=== Topic Frequencies (5 sec sample) ==="
	@$(SOURCE) && \
		echo "--- LiDAR ---" && timeout 5 ros2 topic hz /robocept/lidar/scan 2>&1 | tail -2; \
		echo "--- Camera ---" && timeout 5 ros2 topic hz /robocept/camera/color/image_raw 2>&1 | tail -2; \
		echo "--- Odom ---" && timeout 5 ros2 topic hz /odom 2>&1 | tail -2; \
		echo "--- cmd_vel ---" && timeout 5 ros2 topic hz /cmd_vel 2>&1 | tail -2; \
		true

## Show robot odometry (position)
dev.info.odom:
	@$(SOURCE) && ros2 topic echo /odom --once 2>&1 | head -20

## Show LiDAR scan summary
dev.info.lidar:
	@$(SOURCE) && ros2 topic echo /robocept/lidar/scan --once 2>&1 | head -15

## Show TF tree
dev.info.tf:
	@$(SOURCE) && ros2 run tf2_tools view_frames 2>&1 && echo "Saved frames.pdf"

## Capture simulation images (color, depth, lidar) to /tmp/
dev.capture.sim:
	@echo "=== Capturing simulation sensor data ==="
	@$(SOURCE) && python3 $(SRC_DIR)/robocept_system/test/capture_sim.py

# ============================================================================
# DEV — STOP / CLEAN
# ============================================================================

## Stop simulation
dev.stop.sim:
	@echo "=== Stopping simulation ==="
	@pkill -f "ign gazebo" 2>/dev/null || true
	@pkill -f "parameter_bridge" 2>/dev/null || true
	@pkill -f "robot_state_publisher" 2>/dev/null || true
	@pkill -f "ros2.launch" 2>/dev/null || true
	@echo "Done."

## Stop obstacle avoider
dev.stop.obstacle:
	@pkill -f "obstacle_avoider" 2>/dev/null || true

## Stop all ROS 2 nodes
dev.stop.all:
	@echo "=== Stopping all robocept processes ==="
	@pkill -f "ign gazebo" 2>/dev/null || true
	@pkill -f "parameter_bridge" 2>/dev/null || true
	@pkill -f "robot_state_publisher" 2>/dev/null || true
	@pkill -f "obstacle_avoider" 2>/dev/null || true
	@pkill -f "waypoint_nav" 2>/dev/null || true
	@pkill -f "teleop_twist_keyboard" 2>/dev/null || true
	@pkill -f "ros2.launch" 2>/dev/null || true
	@pkill -f "ros2.bag" 2>/dev/null || true
	@echo "All stopped."

## Clean build artifacts
dev.clean:
	@echo "=== Cleaning workspace ==="
	@rm -rf $(WS_DIR)/build $(WS_DIR)/install $(WS_DIR)/log
	@echo "Done. Run: make dev.build.all"

# ============================================================================
# PROD — REAL HARDWARE
# ============================================================================

## Launch full perception stack (LiDAR + camera + health monitor)
prod.run.perception:
	@echo "=== Launching perception (real hardware) ==="
	@$(SOURCE) && ros2 launch robocept_bringup perception.launch.py \
		2>&1 | tee $(LOG_DIR)/perception.log

## Launch LiDAR only
prod.run.lidar:
	@$(SOURCE) && ros2 launch robocept_bringup lidar.launch.py \
		2>&1 | tee $(LOG_DIR)/lidar.log

## Launch RealSense only
prod.run.realsense:
	@$(SOURCE) && ros2 launch robocept_bringup realsense.launch.py \
		2>&1 | tee $(LOG_DIR)/realsense.log

## Launch full robot (perception + control + nav)
prod.run.all:
	@echo "=== Launching full robot stack ==="
	@$(SOURCE) && ros2 launch robocept_system robot.launch.py \
		2>&1 | tee $(LOG_DIR)/robot.log

## Record a bag of all topics
prod.run.record:
	@echo "=== Recording bag to /tmp/robocept_bag ==="
	@$(SOURCE) && ros2 launch robocept_bringup recording.launch.py \
		bag_dir:=/tmp/robocept_bag 2>&1 | tee $(LOG_DIR)/recording.log

## Replay a bag (usage: make prod.run.replay BAG=/path/to/bag)
prod.run.replay:
	@echo "=== Replaying bag: $(BAG) ==="
	@$(SOURCE) && ros2 bag play $(BAG) --clock

## Check perception health
prod.info.health:
	@$(SOURCE) && ros2 topic echo /robocept/status --once

## Check diagnostics
prod.info.diag:
	@$(SOURCE) && ros2 topic echo /diagnostics --once

## Verify all packages are installed
prod.info.packages:
	@$(SOURCE) && ros2 pkg list | grep robocept

# ============================================================================
# SETUP — First-time workspace setup
# ============================================================================

## Clone all repos and set up workspace (run once)
setup.workspace:
	@echo "=== Setting up robocept workspace ==="
	@mkdir -p $(SRC_DIR)
	@cd $(SRC_DIR) && \
		(test -d robocept || git clone https://github.com/WashyKK/robocept.git) && \
		(test -d robocept-control || git clone https://github.com/WashingtonKK/robocept-control.git) && \
		(test -d robocept-nav || git clone https://github.com/WashingtonKK/robocept-nav.git) && \
		(test -d robocept-ai || git clone https://github.com/WashingtonKK/robocept-ai.git) && \
		(test -d robocept-bringup || git clone https://github.com/WashingtonKK/robocept-bringup.git)
	@echo "Workspace ready at $(WS_DIR)"
	@echo "Next: make dev.build.all"

## Install simulation dependencies
setup.sim:
	@echo "=== Installing simulation dependencies ==="
	sudo apt-get update -qq
	sudo apt-get install -y \
		ros-humble-ros-gz \
		ros-humble-ros-gz-sim \
		ros-humble-ros-gz-bridge \
		ros-humble-ros-gz-image \
		ros-humble-xacro \
		ros-humble-robot-state-publisher \
		ros-humble-teleop-twist-keyboard
	@echo "Done."

## Install all ROS dependencies
setup.deps:
	@echo "=== Installing all ROS dependencies ==="
	sudo apt-get update -qq
	sudo apt-get install -y \
		ros-humble-ros-gz \
		ros-humble-ros-gz-sim \
		ros-humble-ros-gz-bridge \
		ros-humble-xacro \
		ros-humble-robot-state-publisher \
		ros-humble-teleop-twist-keyboard \
		ros-humble-realsense2-camera \
		ros-humble-cv-bridge \
		ros-humble-vision-msgs
	@echo "Done."

# ============================================================================
# HELP
# ============================================================================

## Show all available targets
help:
	@echo ""
	@echo "  Robocept Makefile — Command Reference"
	@echo "  ======================================"
	@echo ""
	@echo "  SETUP (run once):"
	@echo "    make setup.workspace       Clone all repos, create workspace"
	@echo "    make setup.sim             Install simulation dependencies"
	@echo "    make setup.deps            Install all ROS dependencies"
	@echo ""
	@echo "  BUILD:"
	@echo "    make dev.build.all         Build all packages"
	@echo "    make dev.build.sim         Build simulation packages only"
	@echo "    make dev.build.nav         Build navigation packages only"
	@echo "    make dev.build.pkg PKG=x   Build specific package"
	@echo ""
	@echo "  DEV — SIMULATION:"
	@echo "    make dev.run.sim           Launch sim (headless)"
	@echo "    make dev.run.sim.gui       Launch sim with Ignition GUI"
	@echo "    make dev.run.sim.bg        Launch sim in background"
	@echo "    make dev.run.teleop        Keyboard teleop (direct)"
	@echo "    make dev.run.teleop.safe   Keyboard teleop (through obstacle avoider)"
	@echo ""
	@echo "  DEV — OBSTACLE AVOIDANCE:"
	@echo "    make dev.run.obstacle      Launch obstacle avoider"
	@echo "    make dev.run.nav           Launch full nav stack"
	@echo "    make dev.test.obstacle     Automated obstacle avoidance test"
	@echo "    make dev.test.obstacle.unit  Unit tests (no sim needed)"
	@echo ""
	@echo "  DEV — MONITORING:"
	@echo "    make dev.info.topics       List all topics"
	@echo "    make dev.info.hz           Show topic frequencies"
	@echo "    make dev.info.odom         Show robot position"
	@echo "    make dev.info.lidar        Show LiDAR scan"
	@echo "    make dev.capture.sim       Capture sim images"
	@echo ""
	@echo "  DEV — STOP:"
	@echo "    make dev.stop.sim          Stop simulation"
	@echo "    make dev.stop.obstacle     Stop obstacle avoider"
	@echo "    make dev.stop.all          Stop everything"
	@echo "    make dev.clean             Clean build artifacts"
	@echo ""
	@echo "  PROD — REAL HARDWARE:"
	@echo "    make prod.run.perception   LiDAR + camera + health"
	@echo "    make prod.run.lidar        LiDAR only"
	@echo "    make prod.run.realsense    RealSense only"
	@echo "    make prod.run.all          Full robot stack"
	@echo "    make prod.run.record       Record bag"
	@echo "    make prod.run.replay BAG=x Replay bag"
	@echo "    make prod.info.health      Check perception health"
	@echo "    make prod.info.packages    List installed packages"
	@echo ""

.PHONY: help dev.build.all dev.build.pkg dev.build.sim dev.build.nav \
        dev.run.sim dev.run.sim.gui dev.run.sim.bg dev.run.teleop dev.run.teleop.safe \
        dev.run.obstacle dev.run.nav dev.test.obstacle dev.test.obstacle.unit \
        dev.nav.goto dev.nav.stop \
        dev.info.topics dev.info.hz dev.info.odom dev.info.lidar dev.info.tf dev.capture.sim \
        dev.stop.sim dev.stop.obstacle dev.stop.all dev.clean \
        prod.run.perception prod.run.lidar prod.run.realsense prod.run.all \
        prod.run.record prod.run.replay prod.info.health prod.info.diag prod.info.packages \
        setup.workspace setup.sim setup.deps
