"""Analyse technique d'un dépôt de modèle et conseil de téléchargement."""

from __future__ import annotations

import re
import shlex
from dataclasses import asdict, dataclass
from typing import Any, Literal

from src.api_client import ModelDetails, ModelFile

CompatibilityState = Literal["detected", "probable", "conversion", "not_detected"]

_FAMILY_NAMES = {
    "bert": "BERT",
    "clip": "CLIP",
    "deepseek_v2": "DeepSeek V2",
    "deepseek_v3": "DeepSeek V3",
    "falcon": "Falcon",
    "gemma": "Gemma",
    "gemma2": "Gemma 2",
    "gemma3": "Gemma 3",
    "gpt2": "GPT-2",
    "llama": "Llama",
    "mistral": "Mistral",
    "mixtral": "Mixtral",
    "mllama": "Llama multimodal",
    "phi3": "Phi-3",
    "qwen2": "Qwen 2",
    "qwen2_moe": "Qwen 2 MoE",
    "qwen3": "Qwen 3",
    "roberta": "RoBERTa",
    "t5": "T5",
    "whisper": "Whisper",
}

_ESSENTIAL_BASENAMES = {
    "added_tokens.json",
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model_index.json",
    "modules.json",
    "preprocessor_config.json",
    "processor_config.json",
    "special_tokens_map.json",
    "sentence_bert_config.json",
    "config_sentence_transformers.json",
    "spiece.model",
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
    "vocab.json",
    "vocab.txt",
}


@dataclass(frozen=True, slots=True)
class TechnicalProfile:
    """Caractéristiques d'architecture extraites de configurations hétérogènes."""

    model_classes: tuple[str, ...]
    family: str
    parameters: int | None
    dtype: str
    context_length: int | None
    vocabulary_size: int | None
    quantization: str

    def to_dict(self) -> dict[str, Any]:
        """Convertir le profil en dictionnaire sérialisable."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CompatibilityFinding:
    """Compatibilité détectée avec son niveau de confiance et son indice."""

    name: str
    state: CompatibilityState
    reason: str

    def to_dict(self) -> dict[str, str]:
        """Convertir le résultat en dictionnaire sérialisable."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DownloadRecommendation:
    """Conseil concret sur les poids à récupérer et la commande associée."""

    strategy: Literal["single_file", "snapshot", "adapter", "metadata_only"]
    headline: str
    explanation: str
    primary_files: tuple[str, ...]
    companion_files: tuple[str, ...]
    estimated_bytes: int | None
    command: str
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convertir le conseil en dictionnaire sérialisable."""
        return asdict(self)


def extract_technical_profile(details: ModelDetails) -> TechnicalProfile:
    """Extraire les champs techniques usuels, y compris dans les sous-configs."""
    config = details.config
    classes = _as_string_tuple(_first_config_value(config, "architectures"))
    model_type = _as_optional_string(_first_config_value(config, "model_type"))
    dtype = _display_scalar(
        _first_config_value(config, "torch_dtype", "dtype", "compute_dtype")
    )
    if dtype == "Non renseigné" and details.tensor_dtypes:
        names = {"F32": "float32", "F16": "float16", "BF16": "bfloat16", "F64": "float64"}
        dtype = ", ".join(names.get(value, value) for value in details.tensor_dtypes)
        dtype += " (Safetensors)"
    context_length = _as_positive_int(
        _first_config_value(
            config,
            "max_position_embeddings",
            "max_sequence_length",
            "model_max_length",
            "n_positions",
            "seq_length",
        )
    )
    vocabulary_size = _as_positive_int(_first_config_value(config, "vocab_size"))
    return TechnicalProfile(
        model_classes=classes,
        family=_model_family(model_type, classes),
        parameters=details.summary.parameters,
        dtype=dtype,
        context_length=context_length,
        vocabulary_size=vocabulary_size,
        quantization=_detect_quantization(details),
    )


def inspect_compatibility(details: ModelDetails) -> tuple[CompatibilityFinding, ...]:
    """Évaluer les formats et moteurs sans présenter une supposition comme certaine."""
    paths = [item.path.casefold() for item in details.files]
    basenames = [path.rsplit("/", maxsplit=1)[-1] for path in paths]
    tags = {tag.casefold() for tag in details.summary.tags}
    library = (details.summary.library_name or "").casefold()
    profile = extract_technical_profile(details)
    classes = " ".join(profile.model_classes).casefold()
    quantization = profile.quantization.casefold()

    has_transformers = library == "transformers" or "transformers" in tags
    has_safetensors = any(path.endswith(".safetensors") for path in paths)
    has_gguf = any(path.endswith(".gguf") and "mmproj" not in path for path in paths)
    has_gptq = "gptq" in quantization or _contains_marker(paths, tags, "gptq")
    has_awq = "awq" in quantization or _contains_marker(paths, tags, "awq")
    has_mlx = library == "mlx" or _contains_marker(paths, tags, "mlx")
    is_causal_lm = "causallm" in classes or details.summary.pipeline_tag == "text-generation"

    has_transformers_layout = bool(profile.model_classes) and (
        has_safetensors or any(_is_pytorch_weight(path) for path in paths)
    )

    if has_transformers:
        transformers_finding = CompatibilityFinding(
            "Transformers",
            "detected",
            "Bibliothèque ou tag Transformers présent.",
        )
    elif has_transformers_layout:
        transformers_finding = CompatibilityFinding(
            "Transformers",
            "probable",
            "Architecture et poids au format Transformers détectés.",
        )
    else:
        transformers_finding = CompatibilityFinding(
            "Transformers",
            "not_detected",
            "Aucun indice Transformers explicite.",
        )

    findings = [
        transformers_finding,
        _binary_finding(
            "Safetensors",
            has_safetensors,
            "Poids .safetensors présents.",
            "Aucun fichier .safetensors détecté.",
        ),
        _binary_finding(
            "GGUF",
            has_gguf,
            "Poids GGUF présents dans le dépôt.",
            "Aucun poids GGUF détecté.",
        ),
        _binary_finding(
            "GPTQ",
            has_gptq,
            "Quantification GPTQ déclarée ou nommée.",
            "Aucun indice GPTQ détecté.",
        ),
        _binary_finding(
            "AWQ",
            has_awq,
            "Quantification AWQ déclarée ou nommée.",
            "Aucun indice AWQ détecté.",
        ),
        _binary_finding(
            "MLX",
            has_mlx,
            "Format, bibliothèque ou tag MLX détecté.",
            "Aucun indice MLX détecté.",
        ),
    ]

    if "ollama" in tags or "modelfile" in basenames:
        findings.append(CompatibilityFinding("Ollama", "detected", "Tag Ollama ou Modelfile présent."))
    elif has_gguf:
        findings.append(CompatibilityFinding("Ollama", "probable", "Import du fichier GGUF généralement possible."))
    else:
        findings.append(CompatibilityFinding("Ollama", "not_detected", "Aucun artefact Ollama/GGUF détecté."))

    if "vllm" in tags:
        findings.append(CompatibilityFinding("vLLM", "detected", "Tag vLLM déclaré par le dépôt."))
    elif is_causal_lm and (has_transformers or has_safetensors):
        findings.append(CompatibilityFinding("vLLM", "probable", "Architecture causale standard ; validation runtime requise."))
    else:
        findings.append(CompatibilityFinding("vLLM", "not_detected", "Compatibilité non déclarée."))

    if has_gguf:
        findings.append(CompatibilityFinding("llama.cpp", "detected", "Fichier GGUF directement exploitable."))
    elif is_causal_lm and has_transformers:
        findings.append(CompatibilityFinding("llama.cpp", "conversion", "Conversion vers GGUF nécessaire."))
    else:
        findings.append(CompatibilityFinding("llama.cpp", "not_detected", "Aucun GGUF détecté."))

    if "text-generation-inference" in tags or "tgi" in tags:
        findings.append(CompatibilityFinding("TGI", "detected", "Compatibilité TGI déclarée."))
    elif is_causal_lm and has_transformers:
        findings.append(CompatibilityFinding("TGI", "probable", "Modèle causal Transformers ; validation TGI requise."))
    else:
        findings.append(CompatibilityFinding("TGI", "not_detected", "Compatibilité non déclarée."))

    return tuple(findings)


def recommend_download(details: ModelDetails) -> DownloadRecommendation:
    """Déterminer si un fichier suffit ou si le dépôt doit rester un ensemble cohérent."""
    files = tuple(details.files)
    gguf_files = tuple(
        item for item in files if item.path.casefold().endswith(".gguf") and "mmproj" not in item.path.casefold()
    )
    adapter_files = tuple(
        item for item in files if item.path.casefold().endswith(("adapter_model.safetensors", "adapter_model.bin"))
    )
    safetensor_files = tuple(item for item in files if item.path.casefold().endswith(".safetensors"))
    pytorch_files = tuple(item for item in files if _is_pytorch_weight(item.path))
    onnx_files = tuple(item for item in files if item.path.casefold().endswith(".onnx"))
    companion_files = _companion_files(files)
    repo = shlex.quote(details.summary.repo_id)

    if gguf_files:
        chosen = _choose_gguf(gguf_files)
        chosen_files = _gguf_shards(chosen, gguf_files)
        split = bool(re.search(r"-\d{5}-of-\d{5}\.gguf$", chosen.path, flags=re.IGNORECASE))
        projectors = tuple(item for item in files if "mmproj" in item.path.casefold() and item.path.casefold().endswith(".gguf"))
        warnings = []
        if split:
            warnings.append("Ce GGUF est découpé : toutes les parties de la même variante sont indispensables.")
            expected = int(re.search(r"-of-(\d{5})\.gguf$", chosen.path, flags=re.IGNORECASE).group(1))
            if len(chosen_files) != expected:
                warnings.append(f"Attention : seulement {len(chosen_files)} partie(s) sur {expected} sont présentes dans le dépôt.")
        if projectors:
            warnings.append("Modèle multimodal : choisissez également le mmproj compatible indiqué dans la Model Card pour les images.")
        if safetensor_files:
            warnings.append("Conseil pour llama.cpp/Ollama. Pour Transformers, utilisez plutôt les poids Safetensors avec config et tokenizer.")
        return DownloadRecommendation(
            strategy="snapshot" if split else "single_file",
            headline="Téléchargez toutes les parties de la variante GGUF sélectionnée"
            if split
            else "Téléchargez un seul fichier GGUF de la variante sélectionnée",
            explanation=(
                "Pour une utilisation locale avec llama.cpp ou Ollama, choisissez une seule variante GGUF. "
                "Q4_K_M est privilégiée lorsqu’elle existe ; le choix reste à adapter à votre mémoire et à la Model Card."
            ),
            primary_files=tuple(item.path for item in chosen_files),
            companion_files=(),
            estimated_bytes=_sum_known_sizes(chosen_files),
            command=_download_command(repo, chosen_files),
            warning=" ".join(warnings) or None,
        )

    if adapter_files:
        base_model = details.card_data.get("base_model") or details.card_data.get("base_models")
        base_label = _flatten_value(base_model) or "le modèle de base indiqué dans la Model Card"
        selected = adapter_files + tuple(
            item for item in files if item.path.rsplit("/", maxsplit=1)[-1].casefold() == "adapter_config.json"
        )
        return DownloadRecommendation(
            strategy="adapter",
            headline="Téléchargez l’adapter et son modèle de base",
            explanation=(
                f"Ce dépôt contient un adapter PEFT. Les fichiers d’adapter seuls ne fonctionnent pas sans {base_label}."
            ),
            primary_files=tuple(item.path for item in selected),
            companion_files=(),
            estimated_bytes=_sum_known_sizes(selected),
            command=_download_command(repo, selected, directory="./adapter"),
            warning="Le modèle de base doit être téléchargé séparément.",
        )

    if safetensor_files:
        if details.summary.library_name != "diffusers":
            safetensor_files = _select_safetensors(safetensor_files)
        sharded = _is_sharded(safetensor_files, files)
        companion_files = tuple(
            item for item in companion_files
            if not item.path.casefold().endswith(".index.json")
            or (sharded and item.path.casefold().endswith(".safetensors.index.json"))
        )
        quantized = _detect_quantization(details) != "Non détectée"
        qualifier = "quantifié " if quantized else ""
        headline = (
            "Téléchargez tous les shards Safetensors et leurs fichiers de configuration"
            if sharded
            else "Téléchargez le poids Safetensors avec la configuration et le tokenizer"
        )
        warning = (
            "Un shard isolé est inutilisable ; conservez aussi le fichier d’index."
            if sharded
            else "Le fichier de poids seul ne suffit généralement pas au chargement Transformers."
        )
        return DownloadRecommendation(
            strategy="snapshot",
            headline=headline,
            explanation=(
                f"Poids {qualifier}pour {details.summary.library_name or 'la bibliothèque indiquée dans la Model Card'}. "
                "Conservez les poids, configurations et fichiers de prétraitement/tokenizer ensemble."
            ),
            primary_files=tuple(item.path for item in safetensor_files),
            companion_files=tuple(item.path for item in companion_files),
            estimated_bytes=_sum_known_sizes(safetensor_files + companion_files),
            command=_download_command(repo, safetensor_files + companion_files),
            warning=warning,
        )

    if pytorch_files:
        return DownloadRecommendation(
            strategy="snapshot",
            headline="Téléchargez les poids PyTorch avec la configuration et le tokenizer",
            explanation="Les fichiers .bin/.pt ne sont pas autonomes ; gardez l’ensemble du dépôt cohérent.",
            primary_files=tuple(item.path for item in pytorch_files),
            companion_files=tuple(item.path for item in companion_files),
            estimated_bytes=_sum_known_sizes(pytorch_files + companion_files),
            command=_download_command(repo, pytorch_files + companion_files),
            warning="Préférez une variante Safetensors du modèle lorsqu’elle est disponible.",
        )

    if onnx_files:
        return DownloadRecommendation(
            strategy="snapshot",
            headline="Téléchargez les graphes ONNX avec leurs fichiers de pré/post-traitement",
            explanation="Le graphe ONNX doit rester accompagné des fichiers de pré/post-traitement.",
            primary_files=tuple(item.path for item in onnx_files),
            companion_files=tuple(item.path for item in companion_files),
            estimated_bytes=_sum_known_sizes(onnx_files + companion_files),
            command=f"hf download {repo} --local-dir ./model",
        )

    return DownloadRecommendation(
        strategy="metadata_only",
        headline="Aucun fichier de poids reconnu automatiquement",
        explanation="Consultez la Model Card avant de télécharger le snapshot complet.",
        primary_files=(),
        companion_files=tuple(item.path for item in companion_files),
        estimated_bytes=details.used_storage,
        command=f"hf download {repo} --local-dir ./model",
        warning="Le dépôt peut utiliser un format spécialisé non détecté par HF Explorer.",
    )


def classify_file(
    model_file: ModelFile,
    recommendation: DownloadRecommendation,
) -> tuple[str, str, bool]:
    """Décrire le rôle, le format et le caractère recommandé d'un fichier."""
    path = model_file.path
    lower = path.casefold()
    basename = lower.rsplit("/", maxsplit=1)[-1]
    if basename == "readme.md":
        role, file_format = "Documentation / Model Card", "Markdown"
    elif basename == "config.json":
        role, file_format = "Configuration du modèle", "JSON"
    elif basename in {"tokenizer.json", "tokenizer_config.json", "tokenizer.model"}:
        role, file_format = "Tokenizer", path.rsplit(".", maxsplit=1)[-1].upper()
    elif lower.endswith(".safetensors.index.json"):
        role, file_format = "Index des shards", "JSON"
    elif lower.endswith(".safetensors"):
        role, file_format = "Poids du modèle", "Safetensors"
    elif lower.endswith(".gguf") and "mmproj" in lower:
        role, file_format = "Projecteur multimodal", "GGUF"
    elif lower.endswith(".gguf"):
        role, file_format = "Poids quantifiés", "GGUF"
    elif lower.startswith("coreml/") or ".mlpackage/" in lower or lower.endswith(".mlmodel"):
        role, file_format = "Artefact CoreML", "CoreML"
    elif lower.endswith(".msgpack"):
        role, file_format = "Poids du modèle", "Flax"
    elif lower.endswith(".h5"):
        role, file_format = "Poids du modèle", "TensorFlow"
    elif lower.endswith(".ot"):
        role, file_format = "Poids du modèle", "Rust / tch"
    elif basename in {"training_args.bin", "optimizer.bin", "scheduler.bin"}:
        role, file_format = "Artefact d’entraînement", "PyTorch"
    elif lower.endswith((".bin", ".pt", ".pth")):
        role, file_format = "Poids du modèle", "PyTorch"
    elif lower.endswith(".onnx"):
        role, file_format = "Graphe d’inférence", "ONNX"
    elif basename in _ESSENTIAL_BASENAMES:
        role, file_format = "Configuration / prétraitement", path.rsplit(".", maxsplit=1)[-1].upper()
    else:
        role = "Fichier auxiliaire"
        file_format = path.rsplit(".", maxsplit=1)[-1].upper() if "." in basename else "—"
    selected_files = recommendation.primary_files + recommendation.companion_files
    selected = path in selected_files
    return role, file_format, selected


def config_value(config: dict[str, Any], *keys: str) -> Any:
    """Lire une clé de configuration à la racine ou dans ses sous-configurations usuelles.

    Point d'entrée public réutilisé par d'autres modules (comme le calculateur de ressources)
    qui doivent lire des champs d'architecture sans dupliquer la traversée des sous-configs.
    """
    return _first_config_value(config, *keys)


def _first_config_value(config: dict[str, Any], *keys: str) -> Any:
    """Chercher une clé à la racine puis dans les sous-configurations usuelles."""
    sections = [config]
    for section_name in ("text_config", "language_config", "decoder", "model_config"):
        section = config.get(section_name)
        if isinstance(section, dict):
            sections.append(section)
    for key in keys:
        for section in sections:
            value = section.get(key)
            if value is not None:
                return value
    return None


def _detect_quantization(details: ModelDetails) -> str:
    """Identifier la méthode et le nombre de bits depuis config, tags ou fichiers."""
    quantization = _first_config_value(details.config, "quantization_config", "quantization")
    if isinstance(quantization, dict):
        method = quantization.get("quant_method") or quantization.get("method")
        bits = quantization.get("bits") or quantization.get("num_bits")
        if not bits:
            bits = 4 if quantization.get("load_in_4bit") else 8 if quantization.get("load_in_8bit") else None
        group = quantization.get("group_size")
        parts = [str(method).upper() if method else "Quantifiée"]
        if bits:
            parts.append(f"{bits} bits")
        if group:
            parts.append(f"groupe {group}")
        return " · ".join(parts)

    evidence = " ".join(
        [details.summary.repo_id, *details.summary.tags, *(item.path for item in details.files)]
    ).casefold()
    for marker, label in (("gptq", "GPTQ"), ("awq", "AWQ"), ("bnb-4bit", "BitsAndBytes 4 bits"), ("4bit", "4 bits"), ("8bit", "8 bits")):
        if marker in evidence:
            return label
    if any(item.path.casefold().endswith(".gguf") for item in details.files):
        variants = sorted(set(re.findall(r"\bq\d(?:_[a-z0-9]+)+\b", evidence, flags=re.IGNORECASE)))
        return "GGUF" + (" · " + ", ".join(item.upper() for item in variants[:5]) if variants else "")
    return "Non détectée"


def _model_family(model_type: str | None, classes: tuple[str, ...]) -> str:
    """Déduire une famille humaine depuis model_type ou le nom de classe."""
    if model_type:
        normalised = model_type.casefold().replace("-", "_")
        return _FAMILY_NAMES.get(normalised, model_type.replace("_", " ").title())
    if not classes:
        return "Non renseignée"
    class_name = classes[0]
    for suffix in ("ForCausalLM", "ForMaskedLM", "ForSequenceClassification", "Model"):
        class_name = class_name.removesuffix(suffix)
    return class_name or classes[0]


def _binary_finding(
    name: str,
    detected: bool,
    detected_reason: str,
    missing_reason: str,
) -> CompatibilityFinding:
    """Créer un résultat détecté/non détecté homogène."""
    return CompatibilityFinding(
        name=name,
        state="detected" if detected else "not_detected",
        reason=detected_reason if detected else missing_reason,
    )


def _contains_marker(paths: list[str], tags: set[str], marker: str) -> bool:
    """Chercher un marqueur comme mot significatif dans tags et chemins."""
    pattern = re.compile(rf"(?:^|[-_/.]){re.escape(marker)}(?:$|[-_/.])", flags=re.IGNORECASE)
    return any(pattern.search(value) for value in [*paths, *tags])


def _is_pytorch_weight(path: str) -> bool:
    """Reconnaître les poids PyTorch sans confondre les artefacts d'entraînement."""
    lower = path.casefold()
    if lower.startswith("coreml/") or ".mlpackage/" in lower:
        return False
    basename = lower.rsplit("/", maxsplit=1)[-1]
    if basename in {"training_args.bin", "optimizer.bin", "scheduler.bin"}:
        return False
    return basename.endswith((".bin", ".pt", ".pth"))


def _choose_gguf(files: tuple[ModelFile, ...]) -> ModelFile:
    """Choisir une quantification GGUF équilibrée plutôt que la plus petite aveuglément."""
    preferences = ("q4_k_m", "q5_k_m", "q4_k_s", "q5_k_s", "q4_0", "q8_0")

    def rank(item: ModelFile) -> tuple[int, bool, int, str]:
        lower = item.path.casefold()
        preference = next((index for index, token in enumerate(preferences) if token in lower), len(preferences))
        return preference, item.size is None, item.size or 0, lower

    return min(files, key=rank)


def _gguf_shards(chosen: ModelFile, files: tuple[ModelFile, ...]) -> tuple[ModelFile, ...]:
    """Ne jamais conseiller une seule partie d'un GGUF découpé."""
    match = re.match(r"^(.*)-\d{5}-of-(\d{5})\.gguf$", chosen.path, flags=re.IGNORECASE)
    if match is None:
        return (chosen,)
    pattern = re.compile(
        rf"^{re.escape(match.group(1))}-\d{{5}}-of-{match.group(2)}\.gguf$",
        flags=re.IGNORECASE,
    )
    return tuple(sorted((item for item in files if pattern.match(item.path)), key=lambda item: item.path))


def _select_safetensors(files: tuple[ModelFile, ...]) -> tuple[ModelFile, ...]:
    """Préférer le poids canonique à ses variantes redondantes lorsqu'il existe."""
    for name in ("model.safetensors", "pytorch_model.safetensors"):
        canonical = next((item for item in files if item.path == name), None)
        if canonical is not None:
            return (canonical,)
    return files


def _download_command(
    repo: str,
    files: tuple[ModelFile, ...],
    *,
    directory: str = "./model",
) -> str:
    """Générer une commande visant les fichiers exacts, sans glob trop large."""
    filenames = " ".join(shlex.quote(item.path) for item in files)
    return f"hf download {repo} {filenames} --local-dir {directory}"


def _companion_files(files: tuple[ModelFile, ...]) -> tuple[ModelFile, ...]:
    """Sélectionner config, tokenizer et index nécessaires au chargement."""
    selected = []
    for item in files:
        basename = item.path.rsplit("/", maxsplit=1)[-1].casefold()
        if basename in _ESSENTIAL_BASENAMES or item.path.casefold().endswith(".index.json"):
            selected.append(item)
    return tuple(selected)


def _is_sharded(weights: tuple[ModelFile, ...], files: tuple[ModelFile, ...]) -> bool:
    """Détecter un jeu de poids découpé en shards."""
    return len(weights) > 1 and (
        any(re.search(r"-\d{5}-of-\d{5}\.safetensors$", item.path, flags=re.IGNORECASE) for item in weights)
        or any(item.path.casefold().endswith(".safetensors.index.json") for item in files)
    )


def _sum_known_sizes(files: tuple[ModelFile, ...]) -> int | None:
    """Ne pas annoncer un total incomplet comme le volume de l'ensemble."""
    if not files or any(item.size is None for item in files):
        return None
    return sum(item.size or 0 for item in files)


def _as_string_tuple(value: Any) -> tuple[str, ...]:
    """Normaliser une valeur scalaire ou une liste en tuple de chaînes."""
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value)
    return (str(value),)


def _as_optional_string(value: Any) -> str | None:
    """Normaliser une valeur optionnelle en chaîne."""
    return str(value) if value is not None else None


def _as_positive_int(value: Any) -> int | None:
    """Convertir une valeur positive en entier, sans accepter les sentinelles géantes."""
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if 0 < number < 10**12 else None


def _display_scalar(value: Any) -> str:
    """Afficher proprement une valeur technique scalaire."""
    if value is None:
        return "Non renseigné"
    if isinstance(value, str):
        return value.replace("torch.", "")
    return str(value)


def _flatten_value(value: Any) -> str:
    """Aplatir une valeur de métadonnée pour une phrase courte."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key}: {item}" for key, item in value.items())
    return str(value)
