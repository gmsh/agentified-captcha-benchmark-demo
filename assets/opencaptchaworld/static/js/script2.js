let puzzleStartTime = null;
let currentPuzzle = null;
let clickCoordinates = null;
let currentRotationAngle = 0;
let selectedCells = [];
let bingoSelectedCells = [];
let selectedAnimalIndex = -1;

document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const downloadBtn = document.getElementById('download-result');
    const userAnswerInput = document.getElementById('user-answer');
    const puzzleImageContainer = document.querySelector('.puzzle-image-container');
    const resultMessage = document.getElementById('result-message');
    const puzzlePrompt = document.getElementById('puzzle-prompt');
    const puzzleContainer = document.getElementById('puzzle-container');
    const inputGroup = document.querySelector('.input-group');

    // Get URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const puzzleType = urlParams.get('type');
    const puzzleId = urlParams.get('id');

    // Event listeners
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadResult);
    }
    if (userAnswerInput) {
        userAnswerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                downloadResult();
            }
        });
    }

    // Auto-load puzzle if parameters are present
    if (puzzleType && puzzleId) {
        loadPuzzle(puzzleType, puzzleId);
    } else {
        showError('Missing URL parameters. Please provide type and id parameters.<br>Example: /get_puzzle?type=Dice_Count&id=dice1.png');
    }

    // Functions
    function showError(message) {
        puzzleContainer.innerHTML = `<div class="error-message">${message}</div>`;
        puzzleContainer.style.display = 'block';
    }

    function loadPuzzle(puzzleType, puzzleId) {
        // Reset state
        currentPuzzle = null;
        clickCoordinates = null;
        currentRotationAngle = 0;
        selectedCells = [];
        bingoSelectedCells = [];
        selectedAnimalIndex = -1;

        // Show loading state
        puzzleContainer.innerHTML = `
            <div class="puzzle-image-wrapper">
                <div class="puzzle-image-container">
                    <img id="puzzle-image" src="" alt="CAPTCHA Puzzle">
                </div>
            </div>
            <div class="puzzle-question">
                <h3 id="puzzle-prompt">Loading puzzle...</h3>
                <div class="input-group">
                    <input type="text" id="user-answer" placeholder="Your answer">
                    <button id="download-result">Download Result</button>
                </div>
                <div id="result-message" class="result-message"></div>
            </div>
        `;
        puzzleContainer.style.display = 'block';

        // Re-get DOM elements after innerHTML change
        const puzzleImage = document.getElementById('puzzle-image');
        const puzzlePrompt = document.getElementById('puzzle-prompt');
        const newDownloadBtn = document.getElementById('download-result');
        const newUserAnswerInput = document.getElementById('user-answer');
        const newResultMessage = document.getElementById('result-message');
        const newPuzzleImageContainer = document.querySelector('.puzzle-image-container');
        const newInputGroup = document.querySelector('.input-group');

        // Re-attach event listeners
        if (newDownloadBtn) {
            newDownloadBtn.addEventListener('click', () => downloadResult(puzzleType, puzzleId));
        }
        if (newUserAnswerInput) {
            newUserAnswerInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    downloadResult(puzzleType, puzzleId);
                }
            });
        }
        if (puzzleImage) {
            puzzleImage.addEventListener('click', (e) => handleImageClick(e, newPuzzleImageContainer));
        }

        // Fetch puzzle data
        fetch(`/api/get_puzzle?type=${encodeURIComponent(puzzleType)}&id=${encodeURIComponent(puzzleId)}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.error || 'Failed to load puzzle');
                    });
                }
                return response.json();
            })
            .then(data => {
                currentPuzzle = data;
                puzzleStartTime = Date.now();

                console.log('Puzzle data:', data);

                // Set the prompt
                if (puzzlePrompt) {
                    puzzlePrompt.textContent = data.prompt;
                }

                // Handle different puzzle types
                renderPuzzle(data, newPuzzleImageContainer, newInputGroup, puzzleImage);
            })
            .catch(error => {
                console.error('Error loading puzzle:', error);
                showError('Error: ' + error.message);
            });
    }

    function renderPuzzle(data, container, inputGroupEl, puzzleImg) {
        // Clear previous puzzle content
        container.innerHTML = '';

        // Remove any existing controls
        const existingControls = document.querySelectorAll('.rotation-controls, .slider-component, .grid-overlay, .arrow-controls, .hold-button-container');
        existingControls.forEach(el => el.remove());

        // Handle different input types
        const userAnswerInput = document.getElementById('user-answer');

        if (data.input_type === 'rotation') {
            setupRotationControls(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'slide') {
            setupSlidePuzzle(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'multiselect') {
            setupMultiselect(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'image_grid') {
            setupImageGrid(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'bingo_swap') {
            setupBingoGrid(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'image_matching') {
            setupImageMatching(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'patch_select') {
            setupPatchSelect(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'dart_count') {
            setupDartCount(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'object_match') {
            setupObjectMatch(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'select_animal') {
            setupSelectAnimal(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'place_dot') {
            setupPlaceDot(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'connect_icon') {
            setupConnectIcon(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'click_order') {
            setupClickOrder(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'hold_button') {
            setupHoldButton(container);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else if (data.input_type === 'click') {
            // For click type, show the image
            const img = document.createElement('img');
            img.id = 'puzzle-image';
            img.src = data.image_path;
            img.alt = 'CAPTCHA Puzzle';
            img.addEventListener('click', (e) => handleImageClick(e, container));
            container.appendChild(img);
            if (userAnswerInput) userAnswerInput.style.display = 'none';
        } else {
            // For text/number input types
            const img = document.createElement('img');
            img.id = 'puzzle-image';
            img.src = data.image_path;
            img.alt = 'CAPTCHA Puzzle';
            container.appendChild(img);

            if (userAnswerInput) {
                userAnswerInput.style.display = 'block';
                if (data.input_type === 'number') {
                    userAnswerInput.type = 'number';
                } else {
                    userAnswerInput.type = 'text';
                }
            }
        }
    }

    function handleImageClick(e, container) {
        if (currentPuzzle && currentPuzzle.input_type === 'click') {
            // Get click coordinates relative to the image
            const rect = e.target.getBoundingClientRect();
            const x = Math.round(e.clientX - rect.left);
            const y = Math.round(e.clientY - rect.top);

            // Store coordinates for submission
            clickCoordinates = [x, y];

            // Show where user clicked
            showClickMarker(x, y, container);

            console.log('Click received:', { x, y });

            // Show message
            const resultMessage = document.getElementById('result-message');
            if (resultMessage) {
                resultMessage.textContent = `Clicked at (${x}, ${y}). Click "Download Result" to save.`;
                resultMessage.style.color = '#2196F3';
            }
        }
    }

    function showClickMarker(x, y, container) {
        // Remove any existing markers
        const existingMarker = document.querySelector('.click-marker');
        if (existingMarker) {
            existingMarker.remove();
        }

        // Create a marker at the click position
        const marker = document.createElement('div');
        marker.className = 'click-marker';
        marker.style.position = 'absolute';
        marker.style.left = `${x - 5}px`;
        marker.style.top = `${y - 5}px`;
        marker.style.width = '10px';
        marker.style.height = '10px';
        marker.style.borderRadius = '50%';
        marker.style.backgroundColor = 'rgba(33, 150, 243, 0.7)';
        marker.style.border = '2px solid #2196F3';
        marker.style.pointerEvents = 'none';
        marker.style.zIndex = '1000';

        if (container) {
            if (container.style.position !== 'relative') {
                container.style.position = 'relative';
            }
            container.appendChild(marker);
        }
    }

    function downloadResult(puzzleType, puzzleId) {
        if (!currentPuzzle) {
            alert('No puzzle loaded');
            return;
        }

        let answer = null;

        // Get answer based on input type
        const userAnswerInput = document.getElementById('user-answer');
        if (currentPuzzle.input_type === 'number' || currentPuzzle.input_type === 'text') {
            if (!userAnswerInput) {
                alert('Answer input not found');
                return;
            }
            answer = userAnswerInput.value.trim();
            if (!answer) {
                alert('Please provide an answer');
                return;
            }
            if (currentPuzzle.input_type === 'number') {
                answer = parseInt(answer);
            }
        } else if (currentPuzzle.input_type === 'click' || currentPuzzle.input_type === 'place_dot') {
            if (!clickCoordinates) {
                alert('Please click on the image first');
                return;
            }
            answer = clickCoordinates;
        } else if (currentPuzzle.input_type === 'rotation') {
            answer = currentRotationAngle;
        } else if (currentPuzzle.input_type === 'slide') {
            answer = getSliderPosition();
        } else if (currentPuzzle.input_type === 'multiselect' || currentPuzzle.input_type === 'patch_select' || currentPuzzle.input_type === 'select_animal') {
            answer = selectedCells;
        } else if (currentPuzzle.input_type === 'image_grid') {
            answer = getSelectedImages();
        } else if (currentPuzzle.input_type === 'bingo_swap') {
            answer = bingoSelectedCells;
        } else if (currentPuzzle.input_type === 'image_matching' || currentPuzzle.input_type === 'dart_count' || currentPuzzle.input_type === 'object_match' || currentPuzzle.input_type === 'connect_icon') {
            answer = getCurrentOptionIndex();
        } else if (currentPuzzle.input_type === 'click_order') {
            answer = getClickOrderPositions();
        } else if (currentPuzzle.input_type === 'hold_button') {
            answer = getHoldButtonTime();
        } else {
            alert('Unknown input type');
            return;
        }

        // Calculate elapsed time
        const elapsedTime = (Date.now() - puzzleStartTime) / 1000;

        // Create result object
        const result = {
            puzzle_type: puzzleType || currentPuzzle.puzzle_type,
            puzzle_id: puzzleId,
            answer: answer,
            elapsed_time: elapsedTime,
            timestamp: new Date().toISOString()
        };

        // Download as JSON
        const dataStr = JSON.stringify(result, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `result_${currentPuzzle.puzzle_type}_${Date.now()}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        // Show success message
        const resultMessage = document.getElementById('result-message');
        if (resultMessage) {
            resultMessage.textContent = 'Result downloaded successfully!';
            resultMessage.style.color = '#4CAF50';
        }
    }

    // Placeholder functions for different puzzle types
    // These are simplified versions - full implementation would copy from script.js

    function setupRotationControls(container) {
        // Create rotation controls (simplified)
        const rotationControls = document.createElement('div');
        rotationControls.className = 'rotation-controls';
        rotationControls.innerHTML = `
            <button class="rotate-left">&#8630;</button>
            <button class="rotate-right">&#8631;</button>
        `;

        const referenceContainer = document.createElement('div');
        referenceContainer.className = 'reference-image-container';
        referenceContainer.innerHTML = `<img id="reference-image" src="${currentPuzzle.reference_image}" alt="Reference">`;

        const objectContainer = document.createElement('div');
        objectContainer.className = 'object-image-container';
        objectContainer.innerHTML = `<img id="object-image" src="${currentPuzzle.object_image}" alt="Object">`;

        const rotationLayout = document.createElement('div');
        rotationLayout.className = 'rotation-layout';
        rotationLayout.appendChild(referenceContainer);
        rotationLayout.appendChild(objectContainer);

        container.appendChild(rotationLayout);
        container.parentElement.appendChild(rotationControls);

        currentRotationAngle = 0;

        rotationControls.querySelector('.rotate-left').addEventListener('click', () => {
            currentRotationAngle = (currentRotationAngle - 45 + 360) % 360;
            updateObjectRotation();
        });

        rotationControls.querySelector('.rotate-right').addEventListener('click', () => {
            currentRotationAngle = (currentRotationAngle + 45) % 360;
            updateObjectRotation();
        });
    }

    function updateObjectRotation() {
        const objectImg = document.getElementById('object-image');
        if (objectImg && currentPuzzle) {
            const baseName = currentPuzzle.object_base;
            const angles = [0, 45, 90, 135, 180, 225, 270, 315];
            const closestAngle = angles.reduce((prev, curr) =>
                Math.abs(curr - currentRotationAngle) < Math.abs(prev - currentRotationAngle) ? curr : prev
            );

            const rotatedImagePath = `/captcha_data/${currentPuzzle.puzzle_type}/${baseName}_${closestAngle}.png`;
            objectImg.src = rotatedImagePath;
        }
    }

    function setupSlidePuzzle(container) {
        // Clear the container
        container.innerHTML = '';

        // Create a container for the background image
        const backgroundContainer = document.createElement('div');
        backgroundContainer.className = 'background-container';
        backgroundContainer.style.position = 'relative';
        backgroundContainer.style.width = '100%';
        backgroundContainer.style.height = 'auto';

        // Add background image
        const backgroundImg = document.createElement('img');
        backgroundImg.src = currentPuzzle.background_image;
        backgroundImg.alt = 'Slide puzzle background';
        backgroundImg.style.width = '100%';
        backgroundImg.style.height = 'auto';
        backgroundImg.style.display = 'block';
        backgroundImg.id = 'slide-background-img'; // Add ID for easy access
        backgroundContainer.appendChild(backgroundImg);

        // Create draggable slider component
        const sliderComponent = document.createElement('div');
        sliderComponent.className = 'slider-component';
        sliderComponent.style.position = 'absolute';
        sliderComponent.style.cursor = 'move';
        sliderComponent.style.zIndex = '10';
        sliderComponent.style.userSelect = 'none';
        sliderComponent.style.touchAction = 'none';
        // Initial width will be set after images load

        // Add component image
        const componentImg = document.createElement('img');
        componentImg.src = currentPuzzle.component_image;
        componentImg.alt = 'Slide component';
        componentImg.style.width = '100%'; // Will be controlled by container size
        componentImg.style.height = '100%';
        componentImg.style.display = 'block';
        componentImg.draggable = false; // Prevent default dragging behavior
        sliderComponent.appendChild(componentImg);

        // Add slider component to the background container
        backgroundContainer.appendChild(sliderComponent);

        // Add the whole setup to the container
        container.appendChild(backgroundContainer);

        // Function to update component size based on background resize ratio
        const updateComponentSize = () => {
            if (!backgroundImg.complete || !componentImg.complete || backgroundImg.naturalWidth === 0) return;

            const containerWidth = backgroundImg.width;
            const containerHeight = backgroundImg.height;
            const naturalWidth = backgroundImg.naturalWidth;
            const naturalHeight = backgroundImg.naturalHeight;

            // Calculate scale ratios
            const scaleX = containerWidth / naturalWidth;
            const scaleY = containerHeight / naturalHeight;

            // Store scales for submission
            backgroundImg.dataset.scaleX = scaleX;
            backgroundImg.dataset.scaleY = scaleY;

            // Calculate component dimensions based on its natural size and the scale
            const componentWidth = componentImg.naturalWidth * scaleX;
            const componentHeight = componentImg.naturalHeight * scaleY;

            sliderComponent.style.width = `${componentWidth}px`;
            sliderComponent.style.height = `${componentHeight}px`;

            // Initial position for the slider component - bottom right corner
            // Only set if not already set (to avoid resetting on window resize if we added that)
            if (!sliderComponent.style.left) {
                const initialLeft = containerWidth - componentWidth - 20;
                const initialTop = containerHeight - componentHeight - 20;

                sliderComponent.style.left = `${initialLeft}px`;
                sliderComponent.style.top = `${initialTop}px`;
            }
        };

        // Wait for images to load
        backgroundImg.onload = updateComponentSize;
        componentImg.onload = updateComponentSize;

        // Trigger onload if images are already cached/loaded
        if (backgroundImg.complete) updateComponentSize();
        if (componentImg.complete) updateComponentSize();

        // Set up draggable functionality
        let isDragging = false;
        let startX, startY, startLeft, startTop;

        // Mouse events for desktop
        sliderComponent.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startLeft = parseInt(sliderComponent.style.left) || 0;
            startTop = parseInt(sliderComponent.style.top) || 0;
            sliderComponent.style.opacity = '0.8';

            // Prevent default browser behavior
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            // Calculate new position
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            // Calculate new position
            let newLeft = startLeft + deltaX;
            let newTop = startTop + deltaY;

            // Get container dimensions
            const containerRect = backgroundContainer.getBoundingClientRect();
            const sliderRect = sliderComponent.getBoundingClientRect();

            // Ensure the slider stays within the container bounds
            if (newLeft < 0) newLeft = 0;
            if (newTop < 0) newTop = 0;
            if (newLeft > containerRect.width - sliderRect.width)
                newLeft = containerRect.width - sliderRect.width;
            if (newTop > containerRect.height - sliderRect.height)
                newTop = containerRect.height - sliderRect.height;

            sliderComponent.style.left = `${newLeft}px`;
            sliderComponent.style.top = `${newTop}px`;
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                sliderComponent.style.opacity = '1';
            }
        });

        // Touch events for mobile
        sliderComponent.addEventListener('touchstart', (e) => {
            isDragging = true;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            startLeft = parseInt(sliderComponent.style.left) || 0;
            startTop = parseInt(sliderComponent.style.top) || 0;
            sliderComponent.style.opacity = '0.8';

            // Prevent default browser behavior
            e.preventDefault();
        });

        document.addEventListener('touchmove', (e) => {
            if (!isDragging) return;

            // Calculate new position
            const deltaX = e.touches[0].clientX - startX;
            const deltaY = e.touches[0].clientY - startY;

            // Calculate new position
            let newLeft = startLeft + deltaX;
            let newTop = startTop + deltaY;

            // Get container dimensions
            const containerRect = backgroundContainer.getBoundingClientRect();
            const sliderRect = sliderComponent.getBoundingClientRect();

            // Ensure the slider stays within the container bounds
            if (newLeft < 0) newLeft = 0;
            if (newTop < 0) newTop = 0;
            if (newLeft > containerRect.width - sliderRect.width)
                newLeft = containerRect.width - sliderRect.width;
            if (newTop > containerRect.height - sliderRect.height)
                newTop = containerRect.height - sliderRect.height;

            sliderComponent.style.left = `${newLeft}px`;
            sliderComponent.style.top = `${newTop}px`;
        });

        document.addEventListener('touchend', () => {
            if (isDragging) {
                isDragging = false;
                sliderComponent.style.opacity = '1';
            }
        });
    }

    function getSliderPosition() {
        const slider = document.querySelector('.slider-component');
        const backgroundImg = document.getElementById('slide-background-img');

        if (slider && backgroundImg) {
            const left = parseInt(slider.style.left) || 0;
            const top = parseInt(slider.style.top) || 0;

            // Calculate center point in displayed coordinates
            const width = slider.offsetWidth;
            const height = slider.offsetHeight;

            const centerX = left + (width / 2);
            const centerY = top + (height / 2);

            // Normalize to 500px width (which ground truth is based on)
            // If the container is smaller (e.g. mobile), we scale up.
            // If the container is 500px, scale is 1.
            const containerWidth = backgroundImg.width;
            const normalizationScale = 500 / containerWidth;

            const normalizedX = centerX * normalizationScale;
            const normalizedY = centerY * normalizationScale;

            return [Math.round(normalizedX), Math.round(normalizedY)];
        }
        return [0, 0];
    }

    function setupMultiselect(container) {
        // Grid-based selection
        const gridSize = currentPuzzle.grid_size || [2, 3];
        const img = document.createElement('img');
        img.src = currentPuzzle.image_path;
        img.style.width = '100%';
        container.appendChild(img);

        createGridOverlay(gridSize, container);
    }

    function createGridOverlay(gridSize, container) {
        const [rows, cols] = gridSize;
        const gridOverlay = document.createElement('div');
        gridOverlay.className = 'grid-overlay';
        gridOverlay.style.position = 'absolute';
        gridOverlay.style.top = '0';
        gridOverlay.style.left = '0';
        gridOverlay.style.width = '100%';
        gridOverlay.style.height = '100%';
        gridOverlay.style.display = 'grid';
        gridOverlay.style.gridTemplateRows = `repeat(${rows}, 1fr)`;
        gridOverlay.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

        for (let i = 0; i < rows * cols; i++) {
            const cell = document.createElement('div');
            cell.className = 'grid-cell';
            cell.dataset.index = i;
            cell.style.border = '2px solid rgba(255, 255, 255, 0.3)';
            cell.style.cursor = 'pointer';
            cell.addEventListener('click', () => toggleCellSelection(i, cell));
            gridOverlay.appendChild(cell);
        }

        container.style.position = 'relative';
        container.appendChild(gridOverlay);
    }

    function toggleCellSelection(index, cell) {
        const selectedIndex = selectedCells.indexOf(index);
        if (selectedIndex > -1) {
            selectedCells.splice(selectedIndex, 1);
            cell.style.backgroundColor = 'transparent';
        } else {
            selectedCells.push(index);
            cell.style.backgroundColor = 'rgba(33, 150, 243, 0.5)';
        }
    }

    function setupImageGrid(container) {
        const images = currentPuzzle.images || [];
        const gridSize = currentPuzzle.grid_size || [3, 3];
        const [rows, cols] = gridSize;

        const gridContainer = document.createElement('div');
        gridContainer.className = 'image-grid-container';
        gridContainer.style.display = 'grid';
        gridContainer.style.gridTemplateRows = `repeat(${rows}, 1fr)`;
        gridContainer.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
        gridContainer.style.gap = '5px';

        images.forEach((imgPath, index) => {
            const imgWrapper = document.createElement('div');
            imgWrapper.className = 'grid-image-wrapper';
            imgWrapper.dataset.index = index;
            imgWrapper.style.cursor = 'pointer';
            imgWrapper.style.border = '3px solid transparent';

            const img = document.createElement('img');
            img.src = imgPath;
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'cover';

            imgWrapper.appendChild(img);
            imgWrapper.addEventListener('click', () => toggleImageSelection(index, imgWrapper));
            gridContainer.appendChild(imgWrapper);
        });

        container.appendChild(gridContainer);
    }

    function toggleImageSelection(index, wrapper) {
        const selectedIndex = selectedCells.indexOf(index);
        if (selectedIndex > -1) {
            selectedCells.splice(selectedIndex, 1);
            wrapper.style.border = '3px solid transparent';
        } else {
            selectedCells.push(index);
            wrapper.style.border = '3px solid #2196F3';
        }
    }

    function getSelectedImages() {
        return selectedCells;
    }

    function setupBingoGrid(container) {
        // Grid-based selection for Bingo (allows exactly 2 selections)
        const gridSize = currentPuzzle.grid_size || [3, 3];
        const img = document.createElement('img');
        img.src = currentPuzzle.image_path;
        img.style.width = '100%';
        container.appendChild(img);

        createBingoGridOverlay(gridSize, container);
    }

    function createBingoGridOverlay(gridSize, container) {
        const [rows, cols] = gridSize;
        const gridOverlay = document.createElement('div');
        gridOverlay.className = 'grid-overlay';
        gridOverlay.style.position = 'absolute';
        gridOverlay.style.top = '0';
        gridOverlay.style.left = '0';
        gridOverlay.style.width = '100%';
        gridOverlay.style.height = '100%';
        gridOverlay.style.display = 'grid';
        gridOverlay.style.gridTemplateRows = `repeat(${rows}, 1fr)`;
        gridOverlay.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

        for (let i = 0; i < rows * cols; i++) {
            const cell = document.createElement('div');
            cell.className = 'grid-cell';
            cell.dataset.index = i;
            cell.style.border = '2px solid rgba(255, 255, 255, 0.3)';
            cell.style.cursor = 'pointer';
            cell.addEventListener('click', () => toggleBingoCellSelection(i, cell));
            gridOverlay.appendChild(cell);
        }

        container.style.position = 'relative';
        container.appendChild(gridOverlay);
    }

    function toggleBingoCellSelection(index, cell) {
        const selectedIndex = bingoSelectedCells.indexOf(index);
        if (selectedIndex > -1) {
            // Deselect
            bingoSelectedCells.splice(selectedIndex, 1);
            cell.style.backgroundColor = 'transparent';
        } else {
            // Only allow 2 selections for Bingo
            if (bingoSelectedCells.length < 2) {
                bingoSelectedCells.push(index);
                cell.style.backgroundColor = 'rgba(33, 150, 243, 0.5)';
            } else {
                // Already have 2 selections, need to deselect one first
                alert('You can only select 2 cells. Please deselect one first.');
            }
        }
    }

    function setupImageMatching(container) {
        const referenceImg = document.createElement('img');
        referenceImg.src = currentPuzzle.reference_image;
        referenceImg.style.width = '45%';

        const optionImg = document.createElement('img');
        optionImg.src = currentPuzzle.option_images[0];
        optionImg.style.width = '45%';
        optionImg.id = 'current-option-image';

        const controls = document.createElement('div');
        controls.className = 'arrow-controls';
        controls.innerHTML = `
            <button class="prev-option">&#8592;</button>
            <button class="next-option">&#8594;</button>
        `;

        const layout = document.createElement('div');
        layout.style.display = 'flex';
        layout.style.justifyContent = 'space-around';
        layout.style.alignItems = 'center';
        layout.appendChild(referenceImg);
        layout.appendChild(optionImg);

        container.appendChild(layout);
        container.parentElement.appendChild(controls);

        let currentIndex = 0;
        window.currentOptionIndex = currentIndex;

        controls.querySelector('.prev-option').addEventListener('click', () => {
            currentIndex = (currentIndex - 1 + currentPuzzle.option_images.length) % currentPuzzle.option_images.length;
            optionImg.src = currentPuzzle.option_images[currentIndex];
            window.currentOptionIndex = currentIndex;  // Update global variable
        });

        controls.querySelector('.next-option').addEventListener('click', () => {
            currentIndex = (currentIndex + 1) % currentPuzzle.option_images.length;
            optionImg.src = currentPuzzle.option_images[currentIndex];
            window.currentOptionIndex = currentIndex;  // Update global variable
        });
    }

    function getCurrentOptionIndex() {
        return window.currentOptionIndex || 0;
    }

    function setupPatchSelect(container) {
        // Clear previous puzzle content
        container.innerHTML = '';

        // Create a container for the patch select grid
        const gridContainer = document.createElement('div');
        gridContainer.className = 'patch-select-grid';

        // Get grid dimensions from the puzzle data
        const gridSize = currentPuzzle.grid_size || [6, 6];
        const rows = gridSize[0];
        const cols = gridSize[1];

        // Set grid styles
        gridContainer.style.display = 'grid';
        gridContainer.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
        gridContainer.style.gridTemplateRows = `repeat(${rows}, 1fr)`;
        gridContainer.style.gap = '3px';
        gridContainer.style.width = '100%';
        gridContainer.style.aspectRatio = `${cols}/${rows}`;
        gridContainer.style.position = 'relative';

        // Create image container
        const imageContainer = document.createElement('div');
        imageContainer.className = 'patch-select-image-container';
        imageContainer.style.position = 'absolute';
        imageContainer.style.top = '0';
        imageContainer.style.left = '0';
        imageContainer.style.width = '100%';
        imageContainer.style.height = '100%';
        imageContainer.style.zIndex = '0';

        // Add the puzzle image
        const img = document.createElement('img');
        img.src = currentPuzzle.image_path;
        img.alt = 'CAPTCHA image';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        imageContainer.appendChild(img);

        // Add image container to grid container
        gridContainer.appendChild(imageContainer);

        // Create grid cells for selection
        for (let i = 0; i < rows * cols; i++) {
            const cell = document.createElement('div');
            cell.className = 'patch-select-cell';
            cell.dataset.index = i;
            cell.style.position = 'relative';
            cell.style.zIndex = '1';
            cell.style.cursor = 'pointer';

            // Add a checkmark icon to indicate selection
            const checkmark = document.createElement('div');
            checkmark.className = 'checkmark';
            checkmark.innerHTML = '✓';
            checkmark.style.position = 'absolute';
            checkmark.style.top = '50%';
            checkmark.style.left = '50%';
            checkmark.style.transform = 'translate(-50%, -50%)';
            checkmark.style.color = 'white';
            checkmark.style.fontSize = '32px';
            checkmark.style.fontWeight = 'bold';
            checkmark.style.opacity = '0';
            checkmark.style.transition = 'opacity 0.2s ease';
            checkmark.style.pointerEvents = 'none';
            checkmark.style.textShadow = '1px 1px 3px rgba(0, 0, 0, 0.7)';
            checkmark.style.zIndex = '3';
            cell.appendChild(checkmark);

            // Add click event to toggle selection
            cell.addEventListener('click', () => {
                // Toggle selection
                if (cell.classList.contains('selected')) {
                    cell.classList.remove('selected');
                    // Hide checkmark
                    checkmark.style.opacity = '0';
                    // Remove from selected array
                    const index = selectedCells.indexOf(i);
                    if (index > -1) {
                        selectedCells.splice(index, 1);
                    }
                } else {
                    cell.classList.add('selected');
                    // Show checkmark
                    checkmark.style.opacity = '1';
                    // Add to selected array
                    selectedCells.push(i);
                }

                // Log selected patches for debugging
                console.log('Selected patches:', selectedCells);
            });

            gridContainer.appendChild(cell);
        }

        container.appendChild(gridContainer);
    }

    function setupDartCount(container) {
        setupImageMatching(container); // Similar to image matching
    }

    function setupObjectMatch(container) {
        setupImageMatching(container); // Similar to image matching
    }

    function setupSelectAnimal(container) {
        setupMultiselect(container); // Similar to multiselect
    }

    function setupPlaceDot(container) {
        // Clear container
        container.innerHTML = '';

        // Create a container for the image with relative positioning
        const imgContainer = document.createElement('div');
        imgContainer.style.position = 'relative';
        imgContainer.style.width = '100%';
        imgContainer.style.maxWidth = '800px';
        imgContainer.style.margin = '0 auto';

        // Create and add the image
        const img = document.createElement('img');
        img.src = currentPuzzle.image_path;
        img.alt = 'Car path image';
        img.style.width = '100%';
        img.style.display = 'block';
        img.style.cursor = 'crosshair';
        imgContainer.appendChild(img);

        // Reset any previous click coordinates
        clickCoordinates = null;

        // Add click handler to the image
        img.addEventListener('click', (e) => {
            // Remove any existing dot
            const existingDot = imgContainer.querySelector('.place-dot-marker');
            if (existingDot) {
                existingDot.remove();
            }

            // Get click coordinates relative to the image
            const rect = e.target.getBoundingClientRect();
            const x = Math.round(e.clientX - rect.left);
            const y = Math.round(e.clientY - rect.top);

            // Store coordinates for submission
            clickCoordinates = [x, y];

            // Create dot marker
            const dot = document.createElement('div');
            dot.className = 'place-dot-marker';
            dot.style.position = 'absolute';
            dot.style.width = '20px';
            dot.style.height = '20px';
            dot.style.borderRadius = '50%';
            dot.style.backgroundColor = 'rgba(255, 0, 0, 0.7)';
            dot.style.border = '2px solid #ff0000';
            dot.style.left = `${x}px`;
            dot.style.top = `${y}px`;
            dot.style.transform = 'translate(-50%, -50%)';
            dot.style.pointerEvents = 'none';
            dot.style.zIndex = '10';

            // Add dot to container
            imgContainer.appendChild(dot);

            // Show message
            const resultMessage = document.getElementById('result-message');
            if (resultMessage) {
                resultMessage.textContent = `Dot placed at (${x}, ${y}). Click "Download Result" to save.`;
                resultMessage.style.color = '#2196F3';
            }
        });

        container.appendChild(imgContainer);
    }

    function setupConnectIcon(container) {
        setupImageMatching(container); // Similar to image matching
    }

    function setupClickOrder(container) {
        // Show reference image
        const orderImg = document.createElement('img');
        orderImg.src = currentPuzzle.order_image;
        orderImg.style.width = '40%';
        orderImg.style.marginBottom = '10px';

        // Create a wrapper for the puzzle image with relative positioning
        const puzzleImgWrapper = document.createElement('div');
        puzzleImgWrapper.style.position = 'relative';
        puzzleImgWrapper.style.width = '100%';

        const puzzleImg = document.createElement('img');
        puzzleImg.id = 'puzzle-image';
        puzzleImg.src = currentPuzzle.image_path;

        puzzleImg.style.maxWidth = '100%';
        puzzleImg.style.height = 'auto';
        puzzleImg.style.maxHeight = 'none';
        puzzleImg.style.display = 'block';

        puzzleImgWrapper.appendChild(puzzleImg);

        const layout = document.createElement('div');
        layout.appendChild(orderImg);
        layout.appendChild(puzzleImgWrapper);
        container.appendChild(layout);

        window.clickOrderPositions = [];

        puzzleImg.addEventListener('click', (e) => {
            const rect = e.target.getBoundingClientRect();
            const x = Math.round(e.clientX - rect.left);
            const y = Math.round(e.clientY - rect.top);
            window.clickOrderPositions.push([x, y]);
            showClickMarker(x, y, puzzleImgWrapper);
        });
    }

    function getClickOrderPositions() {
        return window.clickOrderPositions || [];
    }

    function setupHoldButton(container) {
        // Clear the puzzle image container first
        container.innerHTML = '';

        // Create a container for the button
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'hold-button-container';
        buttonContainer.style.position = 'relative';
        buttonContainer.style.width = '100%';
        buttonContainer.style.maxWidth = '400px';
        buttonContainer.style.margin = '0 auto';
        buttonContainer.style.textAlign = 'center';

        // If the CAPTCHA has an image, show it above the button
        if (currentPuzzle.image_path) {
            const imageElement = document.createElement('img');
            imageElement.src = currentPuzzle.image_path;
            imageElement.alt = 'Hold Button CAPTCHA';
            imageElement.style.display = 'block';
            imageElement.style.width = '100%';
            imageElement.style.maxWidth = '400px';
            imageElement.style.margin = '0 auto 20px';
            imageElement.style.borderRadius = '8px';
            buttonContainer.appendChild(imageElement);
        }

        // Create button element
        const holdButton = document.createElement('div');
        holdButton.className = 'hold-button';
        holdButton.style.position = 'relative';
        holdButton.style.width = '100%';
        holdButton.style.height = 'auto';
        holdButton.style.cursor = 'pointer';
        holdButton.style.userSelect = 'none';
        holdButton.style.borderRadius = '50px';
        holdButton.style.border = '3px solid #333';
        holdButton.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
        holdButton.style.backgroundColor = '#f8f8f8';
        holdButton.style.padding = '30px 0';
        holdButton.style.fontSize = '28px';
        holdButton.style.fontWeight = 'bold';
        holdButton.style.color = '#333';
        holdButton.style.textAlign = 'center';
        holdButton.style.transition = 'background-color 0.3s';
        holdButton.textContent = 'HOLD';

        // Create progress bar
        const progressBar = document.createElement('div');
        progressBar.className = 'hold-progress';
        progressBar.style.position = 'absolute';
        progressBar.style.left = '0';
        progressBar.style.bottom = '0';
        progressBar.style.height = '8px';
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = '#4CAF50';
        progressBar.style.transition = 'width 0.1s linear';
        progressBar.style.borderRadius = '0 0 50px 50px';

        holdButton.appendChild(progressBar);
        buttonContainer.appendChild(holdButton);
        container.appendChild(buttonContainer);

        const requiredHoldTime = currentPuzzle.hold_time || 3; // seconds
        let isHolding = false;
        let holdStartTime = 0;
        let holdTimer = null;
        let completed = false;
        let currentHoldTime = 0;

        // Add event listeners for hold detection
        holdButton.addEventListener('mousedown', startHolding);
        holdButton.addEventListener('touchstart', startHolding);
        document.addEventListener('mouseup', stopHolding);
        document.addEventListener('touchend', stopHolding);

        function startHolding(e) {
            if (completed) return;

            // Prevent default behaviors for touch
            if (e.type === 'touchstart') {
                e.preventDefault();
            }

            isHolding = true;
            holdStartTime = Date.now();
            holdButton.style.backgroundColor = '#e0e0e0';

            // Start progress animation
            holdTimer = setInterval(() => {
                if (!isHolding) return;

                const elapsedTime = (Date.now() - holdStartTime) / 1000; // in seconds
                currentHoldTime = elapsedTime;

                // Update progress bar
                const progress = Math.min((elapsedTime / requiredHoldTime) * 100, 100);
                progressBar.style.width = `${progress}%`;

                // Check if hold is complete
                if (elapsedTime >= requiredHoldTime && !completed) {
                    completeHold();
                }
            }, 100); // Update every 100ms
        }

        function stopHolding() {
            if (!isHolding || completed) return;

            isHolding = false;
            holdButton.style.backgroundColor = '#f8f8f8';

            // Reset progress if not completed
            if (!completed) {
                progressBar.style.width = '0%';
                clearInterval(holdTimer);
            }
        }

        function completeHold() {
            completed = true;
            clearInterval(holdTimer);

            // Change button appearance
            holdButton.style.backgroundColor = '#4CAF50';
            holdButton.style.color = 'white';
            holdButton.textContent = 'COMPLETED';

            const resultMessage = document.getElementById('result-message');
            if (resultMessage) {
                resultMessage.textContent = `Button hold completed! (${currentHoldTime.toFixed(2)}s) Click 'Download Result' to save.`;
                resultMessage.style.color = '#4CAF50';
            }
        }

        window.holdButtonTime = () => currentHoldTime;
    }

    function getHoldButtonTime() {
        return window.holdButtonTime ? window.holdButtonTime() : 0;
    }
});
