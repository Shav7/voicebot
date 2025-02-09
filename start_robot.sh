#!/bin/bash

# Print colorful status messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to handle clean shutdown
cleanup() {
    echo -e "\n${YELLOW}Shutting down robot control system...${NC}"
    
    # Kill the robot control tmux session
    tmux kill-session -t robot_control 2>/dev/null
    
    # Stop MQTT broker
    echo -e "${YELLOW}Stopping MQTT broker...${NC}"
    sudo systemctl stop mosquitto
    
    echo -e "${GREEN}Shutdown complete. Goodbye!${NC}"
    exit 0
}

# Set up trap for Ctrl+C
trap cleanup SIGINT SIGTERM

echo -e "${BLUE}=== Robot Voice Control System Setup ===${NC}"

# Function to check if running in virtual environment
check_venv() {
    if [[ -z "${VIRTUAL_ENV}" ]]; then
        echo -e "${YELLOW}No virtual environment detected.${NC}"
        read -p "Would you like to create and activate a virtual environment? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 -m venv .venv
            source .venv/bin/activate
            pip install -r requirements.txt
        else
            echo -e "${RED}Virtual environment is recommended. Continuing anyway...${NC}"
        fi
    else
        echo -e "${GREEN}Virtual environment is active: ${VIRTUAL_ENV}${NC}"
    fi
}

# Function to check and install dependencies
check_dependencies() {
    local missing_deps=()
    
    # Check Python version
    if ! command -v python3 >/dev/null 2>&1; then
        missing_deps+=("python3")
    else
        python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if (( $(echo "$python_version < 3.11" | bc -l) )); then
            echo -e "${RED}Python 3.11 or higher is required. Current version: ${python_version}${NC}"
            exit 1
        fi
    fi

    # Check for tmux
    if ! command -v tmux >/dev/null 2>&1; then
        missing_deps+=("tmux")
    fi

    # Check for mosquitto
    if ! command -v mosquitto >/dev/null 2>&1; then
        missing_deps+=("mosquitto")
    fi

    # If there are missing dependencies, offer to install them
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${YELLOW}The following dependencies are missing:${NC}"
        printf '%s\n' "${missing_deps[@]}"
        read -p "Would you like to install them now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt-get update
            sudo apt-get install -y "${missing_deps[@]}"
        else
            echo -e "${RED}Cannot continue without required dependencies.${NC}"
            exit 1
        fi
    fi
}

# Function to check OpenAI API key
check_api_key() {
    if [ -z "$OPENAI_API_KEY" ]; then
        echo -e "${YELLOW}OpenAI API key is not set.${NC}"
        read -p "Would you like to set it now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter your OpenAI API key: " api_key
            export OPENAI_API_KEY=$api_key
            echo -e "${GREEN}API key set successfully${NC}"
        else
            echo -e "${RED}Cannot continue without OpenAI API key.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}OpenAI API key is set${NC}"
    fi
}

# Function to check USB microphone
check_microphone() {
    echo -e "${YELLOW}Checking audio devices...${NC}"
    if ! command -v arecord >/dev/null 2>&1; then
        echo -e "${YELLOW}Installing ALSA utils...${NC}"
        sudo apt-get install -y alsa-utils
    fi
    
    arecord -l
    echo -e "${YELLOW}Please verify your microphone is listed above.${NC}"
    read -p "Is your microphone detected? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Please connect a microphone and try again.${NC}"
        exit 1
    fi
}

# Function to check ODrive
check_odrive() {
    if [ ! -e "/dev/ttyAMA1" ]; then
        echo -e "${YELLOW}ODrive UART port (/dev/ttyAMA1) not found.${NC}"
        read -p "Would you like to continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}ODrive UART port detected${NC}"
    fi
}

# Function to setup LED support
setup_led() {
    echo -e "${YELLOW}Setting up LED support...${NC}"
    
    # Enable SPI interface
    if ! lsmod | grep -q "spi_bcm2835"; then
        echo -e "${YELLOW}Enabling SPI interface...${NC}"
        sudo raspi-config nonint do_spi 0
    fi
    
    # Check if user is in spi group
    if ! groups | grep -q "spi"; then
        echo -e "${YELLOW}Adding user to spi group...${NC}"
        sudo usermod -a -G spi $USER
        echo -e "${YELLOW}Please log out and back in for group changes to take effect${NC}"
    fi
    
    # Install Pi5Neo if not already installed
    if ! pip list | grep -q "Pi5Neo"; then
        echo -e "${YELLOW}Installing Pi5Neo package...${NC}"
        pip install Pi5Neo
    fi
    
    echo -e "${GREEN}LED support setup complete${NC}"
}

# Main setup process
echo -e "${BLUE}Checking prerequisites...${NC}"
check_dependencies
check_venv
check_api_key
check_microphone
check_odrive
setup_led

# Start MQTT broker
if ! pgrep mosquitto >/dev/null; then
    echo -e "${YELLOW}Starting MQTT broker...${NC}"
    sudo systemctl start mosquitto
    sleep 2
    if ! pgrep mosquitto >/dev/null; then
        echo -e "${RED}Failed to start MQTT broker!${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}MQTT broker is running${NC}"

# Create a new tmux session
if command -v tmux >/dev/null 2>&1; then
    # Kill existing session if it exists
    tmux kill-session -t robot_control 2>/dev/null

    # Create new session
    tmux new-session -d -s robot_control

    # Start drive node in first window
    echo -e "${YELLOW}Starting drive node...${NC}"
    tmux send-keys -t robot_control "cd $(dirname $0) && python3 core/node_drive.py" C-m
    
    # Wait for drive node to initialize
    sleep 3
    
    # Create window for voice control
    tmux split-window -h -t robot_control
    echo -e "${YELLOW}Starting voice control...${NC}"
    tmux send-keys -t robot_control.1 "cd $(dirname $0) && python3 tests/test_transcription.py" C-m
    
    echo -e "${GREEN}All components started successfully!${NC}"
    echo -e "${BLUE}=== Quick Guide ===${NC}"
    echo -e "1. Say ${GREEN}'start session'${NC} to begin"
    echo -e "2. Use commands like: ${GREEN}'forward'${NC}, ${GREEN}'back'${NC}, ${GREEN}'left'${NC}, ${GREEN}'right'${NC}, ${GREEN}'stop'${NC}"
    echo -e "3. Say ${GREEN}'end session'${NC} when done"
    echo -e "${YELLOW}Press Ctrl+C once to shutdown everything${NC}"
    
    # Attach to the session
    tmux attach -t robot_control
else
    echo -e "${RED}tmux is not installed. Running in separate terminals...${NC}"
    echo -e "${YELLOW}Starting drive node...${NC}"
    gnome-terminal -- bash -c "cd $(dirname $0) && python3 core/node_drive.py"
    sleep 3
    echo -e "${YELLOW}Starting voice control...${NC}"
    gnome-terminal -- bash -c "cd $(dirname $0) && python3 tests/test_transcription.py"
    
    # Wait for Ctrl+C
    echo -e "${YELLOW}Press Ctrl+C to shutdown everything${NC}"
    while true; do
        sleep 1
    done
fi 