import kagglehub

# Download latest version
path = kagglehub.dataset_download("juhibhojani/house-price")

print("Path to dataset files:", path)