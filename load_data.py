from datasets import load_dataset

def get_attack_prompts():
    attack_prompts = []

    # 1. HackAPrompt dataset
    try:
        print("Loading HackAPrompt...")
        dataset = load_dataset("hackaprompt/hackaprompt-dataset", split="train")
        prompts = [row["prompt"] for row in dataset if row.get("prompt")]
        attack_prompts.extend(prompts[:100])
        print(f"HackAPrompt loaded: {len(prompts[:100])} prompts")
    except Exception as e:
        print(f"HackAPrompt failed: {e}")

    # 2. AdvBench dataset
    try:
        print("Loading AdvBench...")
        dataset = load_dataset("walledai/AdvBench", split="train")
        prompts = [row["prompt"] for row in dataset if row.get("prompt")]
        attack_prompts.extend(prompts[:100])
        print(f"AdvBench loaded: {len(prompts[:100])} prompts")
    except Exception as e:
        print(f"AdvBench failed: {e}")

    return attack_prompts


def get_safe_prompts():
    safe_prompts = []

    try:
        print("Loading safe prompts from PromptBench...")
        dataset = load_dataset("aryanagrawal1/promptbench", split="train")
        prompts = [row["original"] for row in dataset if row.get("original")]
        safe_prompts.extend(prompts[:200])
        print(f"PromptBench loaded: {len(prompts[:200])} safe prompts")
    except Exception as e:
        print(f"PromptBench failed: {e}")

    return safe_prompts


if __name__ == "__main__":
    print("Testing dataset loading...")
    attacks = get_attack_prompts()
    print(f"\nTotal attack prompts: {len(attacks)}")

    safes = get_safe_prompts()
    print(f"Total safe prompts: {len(safes)}")