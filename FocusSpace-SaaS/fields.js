// ─────────────────────────────────────────────────────────────
//  logic/fields.js
//  Field dictionaries and timer group mappings
// ─────────────────────────────────────────────────────────────

// ── Work Fields ───────────────────────────────────────────────

export const WORK_FIELDS = {
  "Technology": [
    "Programming", "Web Development", "Mobile App Development",
    "AI / Machine Learning", "Cybersecurity", "Data Science",
    "DevOps", "Databases", "Embedded Systems",
  ],
  "Design": [
    "Graphic Design", "UI/UX", "Motion Graphics",
    "3D Design", "Video Editing", "Photography",
  ],
  "Business & Management": [
    "Marketing", "Sales", "Accounting", "Human Resources",
    "Project Management", "Entrepreneurship", "Financial Analysis",
  ],
  "Medicine & Health": [
    "Medicine", "Pharmacy", "Nursing", "Dentistry",
    "Physical Therapy", "Nutrition",
  ],
  "Engineering": [
    "Civil Engineering", "Electrical Engineering", "Mechanical Engineering",
    "Chemical Engineering", "Architecture", "Electronics Engineering",
  ],
  "Law": [
    "Legal Research", "Contracts", "Commercial Law", "International Law",
  ],
  "Languages & Translation": [
    "Translation", "Language Teaching", "Linguistics",
  ],
  "Media & Writing": [
    "Journalism", "Content Writing", "Copywriting",
    "Authoring", "Script Writing",
  ],
  "Education": [
    "Studying", "Academic Research", "Exam Preparation", "Curriculum Design",
  ],
  "Science": [
    "Mathematics", "Physics", "Chemistry", "Biology", "Statistics",
  ],
  "Arts": [
    "Music", "Drawing", "Fine Arts", "Creative Writing",
  ],
  "Other": ["Other"],
};

// ── Study Fields ──────────────────────────────────────────────

export const STUDY_FIELDS = {
  // University
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

  // School — Primary
  "Primary School — Grades 1 to 6": [
    "Arabic Language", "English Language", "Mathematics",
    "Science", "Social Studies", "Islamic Education",
    "Arts & Crafts", "Physical Education", "Computer Basics",
  ],

  // School — Middle
  "Middle School — Grades 7 to 9": [
    "Arabic Language", "English Language", "French Language",
    "Mathematics", "Physics", "Chemistry", "Biology",
    "Geology & Earth Science", "History", "Geography",
    "Civics & National Education", "Islamic Education",
    "Computer Science", "Physical Education", "Arts",
  ],

  // School — High (Science)
  "High School — Grades 10 to 12 (Science Track)": [
    "Arabic Literature & Criticism", "English Language", "French Language",
    "Pure Mathematics", "Applied Mathematics", "Physics", "Chemistry",
    "Biology", "Geology & Environment", "Islamic Education",
    "National Education", "Philosophy & Logic", "Computer Science", "Statistics",
  ],

  // School — High (Arts)
  "High School — Grades 10 to 12 (Arts / Humanities Track)": [
    "Arabic Literature & Criticism", "English Language", "French Language",
    "History", "Geography", "Philosophy & Logic", "Psychology & Sociology",
    "Economics", "Islamic Education", "National Education",
    "Mathematics", "Statistics", "Arts",
  ],

  "Other": ["Other"],
};

// ── Timer Groups ──────────────────────────────────────────────

export const TIMER_GROUPS = {
  A: new Set([
    "Technology", "Business & Management", "Medicine & Health", "Engineering",
    "Technology & Computer Science", "Business & Economics", "Medicine & Health Sciences",
  ]),
  B: new Set([
    "Design", "Law", "Languages & Translation", "Media & Writing", "Arts",
    "Design & Arts", "Languages",
  ]),
  C: new Set([
    "Education", "Science", "Mathematics", "Natural Sciences", "Social Sciences",
    "History & Humanities", "Education & Teaching",
    "Primary School — Grades 1 to 6",
    "Middle School — Grades 7 to 9",
    "High School — Grades 10 to 12 (Science Track)",
    "High School — Grades 10 to 12 (Arts / Humanities Track)",
  ]),
};

// ── Timer Map (minutes) ───────────────────────────────────────

export const TIMER_MAP = {
  A: { easy: 40, medium: 60, hard: 90 },
  B: { easy: 30, medium: 45, hard: 75 },
  C: { easy: 35, medium: 50, hard: 85 },
};

/**
 * Returns the timer group letter ("A" | "B" | "C" | null) for a given field.
 * @param {string} field
 * @returns {"A" | "B" | "C" | null}
 */
export function getTimerGroup(field) {
  for (const [group, fields] of Object.entries(TIMER_GROUPS)) {
    if (fields.has(field)) return group;
  }
  return null;
}
