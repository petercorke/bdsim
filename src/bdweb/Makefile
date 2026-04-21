FRONTEND_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))frontend
BUILD_DIR    := $(FRONTEND_DIR)/build

.PHONY: help build clean install

help:
	@echo "  make build   - install npm deps (if needed) and build SvelteKit frontend"
	@echo "  make clean   - remove frontend/build/"
	@echo "  make install - npm install only"

build: $(FRONTEND_DIR)/node_modules
	cd $(FRONTEND_DIR) && npm run build
	@echo "[bdweb] Frontend built → $(BUILD_DIR)"

$(FRONTEND_DIR)/node_modules: $(FRONTEND_DIR)/package.json
	cd $(FRONTEND_DIR) && npm install
	@touch $(FRONTEND_DIR)/node_modules  # update mtime so Make doesn't rebuild unnecessarily

install:
	cd $(FRONTEND_DIR) && npm install

clean:
	rm -rf $(BUILD_DIR)
	@echo "[bdweb] Removed $(BUILD_DIR)"
