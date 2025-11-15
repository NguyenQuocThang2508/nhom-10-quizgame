import csv
from typing import List, Union
from pathlib import Path


def _normalize_row(row: dict) -> dict:
    def get(k, alt=''):
        return (row.get(k) or row.get(k.lower()) or row.get(k.upper()) or alt).strip()

    return {
        'question': get('question', ''),
        'A': get('A', ''),
        'B': get('B', ''),
        'C': get('C', ''),
        'D': get('D', ''),
        'answer': get('answer', '').upper()
    }


def load_questions(filenames: Union[str, List[str]] = 'data/questions.csv', max_questions: int = None) -> List[dict]:
    """Load questions from a filename or a list of candidate filenames.

    Returns a list of normalized question dicts with keys:
      'question', 'A', 'B', 'C', 'D', 'answer'
    """
    if isinstance(filenames, str):
        candidates = [filenames]
    else:
        candidates = list(filenames)

    # Resolve relative filenames against the project root (parent of this core package)
    project_root = Path(__file__).resolve().parent.parent
    for filename in candidates:
        questions: List[dict] = []
        try:
            candidate_path = Path(filename)
            if not candidate_path.is_absolute():
                candidate_path = (project_root / candidate_path).resolve()
            with open(candidate_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    q = _normalize_row(row)
                    if not q['question']:
                        continue
                    questions.append(q)
                    if max_questions is not None and len(questions) >= max_questions:
                        break
            if questions:
                print(f"Loaded {len(questions)} questions from {candidate_path}")
                return questions
        except FileNotFoundError:
            continue
        except Exception:
            # ignore parse errors and try next candidate
            continue

    # nothing found or parsed
    return []
