"""
GOMZI BOB - Advanced AI Label Reconstruction & CorelDRAW Vector Engine Package.
"""

from .capability_probe import probe_system_capabilities
from .security_validator import (
    validate_uploaded_file,
    sanitize_svg_strict,
    store_original_artifact,
    load_artifact_metadata,
)
from .font_matcher import match_font_for_region, text_to_svg_path_d, get_ttf_path_for_studio_font
from .smart_importer import (
    detect_file_type_strict,
    import_native_svg,
    import_native_pdf_or_ai,
    extract_cdr_smart,
)
from .hybrid_ocr_layout import analyze_label_text_and_structure
from .vector_cleanplate_engine import reconstruct_flattened_label
from .fidelity_evaluator import evaluate_visual_fidelity
from .vector_exporter import (
    build_coreldraw_svg,
    build_vector_pdf_from_fabric,
    build_coreldraw_exchange_zip,
)
from .print_exporter import render_print_export
from .coreldraw_bridge_client import (
    get_coreldraw_bridge_status,
    bridge_open_in_coreldraw,
    bridge_export_native_cdr,
    bridge_import_native_cdr,
)
from .job_queue import submit_reconstruction_job, get_job_status, cancel_job

__all__ = [
    "probe_system_capabilities",
    "validate_uploaded_file",
    "sanitize_svg_strict",
    "store_original_artifact",
    "load_artifact_metadata",
    "match_font_for_region",
    "text_to_svg_path_d",
    "get_ttf_path_for_studio_font",
    "detect_file_type_strict",
    "import_native_svg",
    "import_native_pdf_or_ai",
    "extract_cdr_smart",
    "analyze_label_text_and_structure",
    "reconstruct_flattened_label",
    "evaluate_visual_fidelity",
    "build_coreldraw_svg",
    "build_vector_pdf_from_fabric",
    "build_coreldraw_exchange_zip",
    "submit_reconstruction_job",
    "get_job_status",
    "cancel_job",
]
