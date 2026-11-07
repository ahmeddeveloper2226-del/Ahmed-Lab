import time

# ── Field dictionaries ────────────────────────────────────────────────────────

work_fields = {
    "Technology": ["Programming", "Web Development", "Mobile App Development", "AI / Machine Learning",
                   "Cybersecurity", "Data Science", "DevOps", "Databases", "Embedded Systems"],
    "Design": ["Graphic Design", "UI/UX", "Motion Graphics", "3D Design", "Video Editing", "Photography"],
    "Business & Management": ["Marketing", "Sales", "Accounting", "Human Resources",
                               "Project Management", "Entrepreneurship", "Financial Analysis"],
    "Medicine & Health": ["Medicine", "Pharmacy", "Nursing", "Dentistry", "Physical Therapy", "Nutrition"],
    "Engineering": ["Civil Engineering", "Electrical Engineering", "Mechanical Engineering",
                    "Chemical Engineering", "Architecture", "Electronics Engineering"],
    "Law": ["Legal Research", "Contracts", "Commercial Law", "International Law"],
    "Languages & Translation": ["Translation", "Language Teaching", "Linguistics"],
    "Media & Writing": ["Journalism", "Content Writing", "Copywriting", "Authoring", "Script Writing"],
    "Education": ["Studying", "Academic Research", "Exam Preparation", "Curriculum Design"],
    "Science": ["Mathematics", "Physics", "Chemistry", "Biology", "Statistics"],
    "Arts": ["Music", "Drawing", "Fine Arts", "Creative Writing"],
    "Other": ["Other"],
}

study_fields = {
    # ── University fields ─────────────────────────────────────────────────────
    "Technology & Computer Science": [
        "Programming Fundamentals", "Data Structures & Algorithms",
        "Web Development", "Mobile Development", "AI & Machine Learning",
        "Cybersecurity", "Data Science", "Cloud Computing",
        "Operating Systems", "Computer Networks", "Software Engineering",
    ],
    "Mathematics": [
        "Algebra", "Calculus", "Discrete Mathematics", "Linear Algebra",
        "Probability & Statistics", "Number Theory", "Geometry",
    ],
    "Natural Sciences": [
        "Physics", "Chemistry", "Biology", "Geology",
        "Astronomy", "Environmental Science", "Biochemistry",
    ],
    "Medicine & Health Sciences": [
        "Anatomy", "Physiology", "Pharmacology", "Pathology",
        "Microbiology", "Nursing Sciences", "Dentistry", "Nutrition Science",
    ],
    "Engineering": [
        "Civil Engineering", "Electrical Engineering", "Mechanical Engineering",
        "Chemical Engineering", "Electronics", "Structural Analysis", "Thermodynamics",
    ],
    "Business & Economics": [
        "Microeconomics", "Macroeconomics", "Accounting", "Finance",
        "Marketing", "Management", "Business Law", "Statistics for Business",
    ],
    "Law": [
        "Constitutional Law", "Criminal Law", "Civil Law",
        "Commercial Law", "International Law", "Human Rights Law",
    ],
    "Languages": [
        "Arabic", "English", "French", "German", "Spanish",
        "Chinese", "Italian", "Japanese", "Translation Studies", "Linguistics",
    ],
    "Social Sciences": [
        "Sociology", "Psychology", "Political Science",
        "Anthropology", "Human Geography", "Philosophy",
    ],
    "History & Humanities": [
        "Ancient History", "Modern History", "World History",
        "Islamic History", "Cultural Studies", "Ethics & Philosophy",
    ],
    "Design & Arts": [
        "Graphic Design Theory", "Art History", "Music Theory",
        "Drawing & Illustration", "Photography", "Film Studies",
    ],
    "Education & Teaching": [
        "Pedagogy", "Educational Psychology", "Curriculum Studies",
        "Special Education", "E-Learning", "Exam Preparation Strategies",
    ],

    # ── School fields ─────────────────────────────────────────────────────────
    "Primary School — Grades 1 to 6": [
        "Arabic Language",
        "English Language",
        "Mathematics",
        "Science",
        "Social Studies",
        "Islamic Education",
        "Arts & Crafts",
        "Physical Education",
        "Computer Basics",
    ],
    "Middle School — Grades 7 to 9": [
        "Arabic Language",
        "English Language",
        "French Language",
        "Mathematics",
        "Physics",
        "Chemistry",
        "Biology",
        "Geology & Earth Science",
        "History",
        "Geography",
        "Civics & National Education",
        "Islamic Education",
        "Computer Science",
        "Physical Education",
        "Arts",
    ],
    "High School — Grades 10 to 12 (Science Track)": [
        "Arabic Literature & Criticism",
        "English Language",
        "French Language",
        "Pure Mathematics",
        "Applied Mathematics",
        "Physics",
        "Chemistry",
        "Biology",
        "Geology & Environment",
        "Islamic Education",
        "National Education",
        "Philosophy & Logic",
        "Computer Science",
        "Statistics",
    ],
    "High School — Grades 10 to 12 (Arts / Humanities Track)": [
        "Arabic Literature & Criticism",
        "English Language",
        "French Language",
        "History",
        "Geography",
        "Philosophy & Logic",
        "Psychology & Sociology",
        "Economics",
        "Islamic Education",
        "National Education",
        "Mathematics",
        "Statistics",
        "Arts",
    ],

    "Other": ["Other"],
}

# ── Timer groups ──────────────────────────────────────────────────────────────

GROUP_A = {
    "Technology", "Business & Management", "Medicine & Health", "Engineering",
    "Technology & Computer Science", "Business & Economics", "Medicine & Health Sciences",
}
GROUP_B = {
    "Design", "Law", "Languages & Translation", "Media & Writing", "Arts",
    "Design & Arts", "Languages", "Law",
}
GROUP_C = {
    "Education", "Science", "Mathematics", "Natural Sciences", "Social Sciences",
    "History & Humanities", "Education & Teaching",
    # School stages all go to group C (academic/educational)
    "Primary School — Grades 1 to 6",
    "Middle School — Grades 7 to 9",
    "High School — Grades 10 to 12 (Science Track)",
    "High School — Grades 10 to 12 (Arts / Humanities Track)",
}

TIMER_MAP = {
    "a": {"easy": 40,  "medium": 60,  "hard": 90},
    "b": {"easy": 30,  "medium": 45,  "hard": 75},
    "c": {"easy": 35,  "medium": 50,  "hard": 85},
}

# ── Helper functions ──────────────────────────────────────────────────────────

def get_task_duration(field: str, difficulty: str) -> int | None:
    difficulty = difficulty.strip().lower()
    if field in GROUP_A:
        return TIMER_MAP["a"].get(difficulty)
    elif field in GROUP_B:
        return TIMER_MAP["b"].get(difficulty)
    elif field in GROUP_C:
        return TIMER_MAP["c"].get(difficulty)
    return None

def timer(minutes: int, task_name: str) -> None:
    seconds = minutes * 60
    print(f"\n🚀 Starting timer for '{task_name}' — {minutes} minute(s)\n")
    while seconds > 0:
        mins, secs = divmod(seconds, 60)
        print(f"\r⏱️  {mins:02d}:{secs:02d}", end="", flush=True)
        time.sleep(1)
        seconds -= 1
    print(f"\r✅ Time's up for '{task_name}'!{' ' * 10}")

def pick_from_list(title: str, options: list) -> tuple[int, str]:
    print(f"\n{title}")
    print("─" * 45)
    for i, option in enumerate(options, start=1):
        print(f"  {i:>2}. {option}")
    print("─" * 45)
    while True:
        raw = input("Enter number: ").strip()
        if raw.isdigit():
            num = int(raw)
            if 1 <= num <= len(options):
                return num - 1, options[num - 1]
        print(f"⚠️  Please enter a number between 1 and {len(options)}.")

def pick_difficulty() -> str:
    _, chosen = pick_from_list("Select Difficulty:", ["easy", "medium", "hard"])
    return chosen

def collect_tasks(label: str, field: str) -> list:
    while True:
        raw = input(f"\nHow many {label} do you have? ").strip()
        if raw.isdigit() and int(raw) > 0:
            count = int(raw)
            break
        print("⚠️  Please enter a valid number greater than 0.")

    tasks = []
    for i in range(count):
        print(f"\n{'─' * 45}")
        print(f"  {label.rstrip('s')} {i + 1} of {count}")
        print(f"{'─' * 45}")
        name       = input(f"{label.rstrip('s')} name: ").strip()
        difficulty = pick_difficulty()
        duration   = get_task_duration(field, difficulty)
        tasks.append({"name": name, "difficulty": difficulty, "duration": duration})
    return tasks

def run_timers(tasks: list, label: str = "Task") -> None:
    print(f"\n{'═' * 45}")
    print(f"  📋 {len(tasks)} {label}(s) ready — Let's go!")
    print(f"{'═' * 45}")

    for idx, task in enumerate(tasks, start=1):
        print(f"\n[{label} {idx}/{len(tasks)}] {task['name']}  |  {task['difficulty'].capitalize()}")
        if task["duration"]:
            print(f"⏳ Allocated time: {task['duration']} minute(s)")
            go = input("Press Enter to start ▶  (or type 'skip'): ").strip().lower()
            if go != "skip":
                timer(task["duration"], task["name"])
            else:
                print(f"⏭️  Skipped timer for '{task['name']}'")
        else:
            print("ℹ️  No preset timer for this field. Good luck!")

    print(f"\n🏁 All {label.lower()}s done! Great job! 💪")

# ── Main flow ─────────────────────────────────────────────────────────────────

_, mode = pick_from_list("📌 What do you want to do?", ["Work", "Studying"])

# ── WORK path ─────────────────────────────────────────────────────────────────
if mode == "Work":
    _, chosen_field    = pick_from_list("📂 Select your Work Field:", list(work_fields.keys()))
    _, chosen_subfield = pick_from_list(f"🔍 Select your {chosen_field} Subfield:", work_fields[chosen_field])

    print(f"\n✅ Field    : {chosen_field}")
    print(f"✅ Subfield : {chosen_subfield}")

    tasks = collect_tasks("Tasks", chosen_field)
    run_timers(tasks, label="Task")

# ── STUDYING path ─────────────────────────────────────────────────────────────
elif mode == "Studying":
    _, chosen_field    = pick_from_list("📚 Select your Study Field:", list(study_fields.keys()))
    _, chosen_subfield = pick_from_list(f"🔍 Select your {chosen_field} Subject:", study_fields[chosen_field])

    print(f"\n✅ Field   : {chosen_field}")
    print(f"✅ Subject : {chosen_subfield}")

    tasks = collect_tasks("Topics", chosen_field)
    run_timers(tasks, label="Topic")