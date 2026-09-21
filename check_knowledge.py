"""Inspect private book ingestion without calling models or changing records."""
from rag.knowledge_base import knowledge_inventory, private_knowledge_dir, search_knowledge


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", help="Optional retrieval check; prints source names and scores only")
    args = parser.parse_args()
    print("私有资料目录：", private_knowledge_dir())
    rows = knowledge_inventory()
    for row in rows:
        print(f"{row['资料']} | {row['状态']} | {row['片段数']}个片段")
    if not rows:
        print("没有发现PDF或UTF-8 TXT资料。")
    if args.question:
        results = search_knowledge(args.question)
        for result in results:
            page = f" 第{result['page']}页" if result.get("page") else ""
            print(f"检索：{result['file']}{page} | {result['score']:.4f}")
        if not results:
            print("本次没有找到达到阈值的片段。")
    print("只检查读取和检索；没有修改档案，没有调用外部API。")


if __name__ == "__main__":
    main()
