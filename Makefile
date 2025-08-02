# Rileva il sistema operativo, comandi mkdir e rm
ifdef OS
    # Windows
    MKDIR := mkdir
    RM := del /Q
    RMDIR := rmdir /S /Q
else
    # Unix
    MKDIR := mkdir -p
    RM := rm -f
    RMDIR := rm -rf
endif


SRC_DIR := src
INC_DIR := include
BUILD_DIR := build


SRCS := $(wildcard $(SRC_DIR)/*.cpp)
OBJS := $(SRCS:$(SRC_DIR)/%.cpp=$(BUILD_DIR)/%.o)
TARGET := $(BUILD_DIR)/ytdlp_utility


CXX := g++
CXXFLAGS := -Wall -Wextra -std=c++23 -I$(INC_DIR)


LDFLAGS :=


all: $(BUILD_DIR) $(TARGET)


$(BUILD_DIR):
	$(MKDIR) $(BUILD_DIR)


$(TARGET): $(OBJS)
	$(CXX) $(OBJS) -o $@ $(LDFLAGS)


$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@


clean:
ifdef OS
	if exist $(BUILD_DIR) $(RMDIR) $(BUILD_DIR)
else
	$(RMDIR) $(BUILD_DIR)
endif

.PHONY: all clean