from pathlib import Path
from uuid import uuid4

from baby import load_baby, save_baby
from sklearn.feature_extraction.text import (
    TfidfVectorizer,
)
from sklearn.metrics.pairwise import (
    cosine_similarity,
)
from storage import data_path

UPLOAD_DIR = data_path("uploads")

ALLOWED_IMAGE_TYPES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


def validate_photo_name(file_name):

    suffix = Path(file_name).suffix.lower()

    if suffix not in ALLOWED_IMAGE_TYPES:

        raise ValueError(
            f"不支持的图片格式：{suffix}"
        )

    return suffix


def create_photo_memory(
    event,
    description,
    event_date,
    photos,
    context_id=None
):

    if not event.strip():

        raise ValueError(
            "回忆标题不能为空。"
        )

    if not photos or len(photos) > 20:
        raise ValueError("每次请上传1到20张照片。")
    if any(len(photo["content"]) > 10 * 1024 * 1024 for photo in photos):
        raise ValueError("单张照片不能超过10MB。")

    memory_id = uuid4().hex

    memory_folder = (
        UPLOAD_DIR
        / memory_id
    )

    validated_photos = []

    for photo in photos:

        suffix = validate_photo_name(
            photo["name"]
        )

        validated_photos.append({
            "content": photo["content"],
            "suffix": suffix
        })


    memory_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    photo_paths = []

    for index, photo in enumerate(
        validated_photos,
        start=1
    ):

        file_name = (
            f"photo_{index}"
            f"{photo['suffix']}"
        )

        file_path = (
            memory_folder
            / file_name
        )

        file_path.write_bytes(
            photo["content"]
        )

        photo_paths.append(
            file_path.as_posix()
        )


    memory_record = {
        "id": memory_id,
        "event": event.strip(),
        "description": description.strip(),
        "date": event_date,
        "photos": photo_paths
    }


    if context_id:
        # The explicit form submit is the user's confirmation for this UI path.
        from agent_v2.service import default_repository
        from agent_v2.engine import add_event
        with default_repository().transaction() as data:
            data["memories"].append(memory_record)
            state = data["_agent_v2"]
            add_event(state, context_id, "ADD", "PHOTO", None, memory_record, "网页用户")
            context = state["contexts"].setdefault(context_id, {})
            context["last_records"] = [memory_record.copy()]
            context["last_command"] = {"action": "QUERY", "entity": "PHOTO", "selector": {"id": memory_id}}
            context["generation"] = context.get("generation", 0) + 1
        return memory_record

    baby = load_baby()

    baby.setdefault(
        "memories",
        []
    ).append(memory_record)

    save_baby(baby)

    return memory_record

def normalize_memory_text(text):

    normalized = text.lower()

    replacements = {
        "站起来": "站立",
        "站着": "站立",
        "走路": "行走",
        "会走": "行走"
    }

    for old_text, new_text in replacements.items():

        normalized = normalized.replace(
            old_text,
            new_text
        )


    stop_words = [
        "宝宝",
        "孩子",
        "第一次",
        "什么时候",
        "最近",
        "现在",
        "照片",
        "回忆",
        "记录",
        "是什么",
        "的",
        "了",
        "吗",
        "？",
        "?"
    ]

    for word in stop_words:

        normalized = normalized.replace(
            word,
            ""
        )


    return normalized.strip()


def get_bigrams(text):

    if len(text) < 2:

        return {text} if text else set()

    return {
        text[index:index + 2]
        for index in range(
            len(text) - 1
        )
    }

def search_photo_memories(
    question,
    top_k=3,
    min_score=0.10
):

    baby = load_baby()

    memories = [
        memory
        for memory in baby.get(
            "memories",
            []
        )
        if memory.get("photos") and not memory.get("_deleted_at")
    ]

    if not memories:

        return []


    normalized_question = (
        normalize_memory_text(
            question
        )
    )

    question_bigrams = get_bigrams(
        normalized_question
    )


    matched_memories = []

    for memory in memories:

        normalized_event = (
            normalize_memory_text(
                memory.get("event", "")
            )
        )

        event_bigrams = get_bigrams(
            normalized_event
        )

        has_exact_match = (
            normalized_event
            and normalized_event
            in normalized_question
        )

        has_bigram_match = bool(
            question_bigrams
            & event_bigrams
        )

        if (
            has_exact_match
            or has_bigram_match
        ):

            matched_memories.append(
                memory
            )


    memories = matched_memories

    if not memories:

        return []

    memory_texts = [
        (
            memory.get("event", "")
            + " "
            + memory.get(
                "description",
                ""
            )
        )
        for memory in memories
    ]


    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4)
    )

    memory_vectors = (
        vectorizer.fit_transform(
            memory_texts
        )
    )

    question_vector = (
        vectorizer.transform(
            [question]
        )
    )

    similarities = cosine_similarity(
        question_vector,
        memory_vectors
    )[0]

    ranked_indexes = (
        similarities.argsort()[::-1]
    )


    results = []

    for index in ranked_indexes:

        score = float(
            similarities[index]
        )

        if score < min_score:

            continue

        result = dict(
            memories[index]
        )

        result["score"] = score

        results.append(result)

        if len(results) >= top_k:

            break


    return results
