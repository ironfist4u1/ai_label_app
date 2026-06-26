from dataclasses import dataclass


@dataclass
class SidebarConfig:
    deep_dive: bool = False
    batch_mode: bool = False
    image_processing: bool = False
    preprocess_contrast: float = 1
    preprocess_size: int = 1500
