"""
Shared constants used across data generation modules.
"""

AD_CATEGORIES = ["tech", "food", "auto", "fashion", "finance", "travel", "health", "gaming"]

AGE_GROUPS = ["13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

# Rough age-group distribution for a global streaming platform audience.
# 13-17 added to represent teen viewers.
AGE_GROUP_WEIGHTS = [0.10, 0.16, 0.24, 0.20, 0.14, 0.10, 0.06]

GENRES = [
    "Action",
    "Comedy",
    "Drama",
    "Sci-Fi",
    "Horror",
    "Documentary",
    "Romance",
    "Thriller",
    "Animation",
    "Fantasy",
]

PROFESSIONS = [
    # General
    "Student",
    "Software Engineer",
    "Teacher",
    "Designer",
    "Doctor",
    "Manager",
    "Writer",
    "Nurse",
    "Accountant",
    "Freelancer",
    "Retired",
    "Marketing Specialist",
    "Data Analyst",
    "Sales Representative",
    "Lawyer",
    # Global variety
    "Entrepreneur",
    "Content Creator",
    "Journalist",
    "Chef",
    "Engineer",
    "Pharmacist",
    "Architect",
    "Consultant",
    "Social Worker",
    "Artist",
    "Mechanic",
    "Farmer",
    "Trader",
    "Researcher",
    "HR Specialist",
]

SEASONS = ["Spring", "Summer", "Fall", "Winter"]

CONTENT_MOODS = ["calm", "uplifting", "playful", "energetic", "intense", "dark"]

TIME_OF_DAY_VALUES = ["morning", "afternoon", "evening", "latenight"]

ADVERTISERS = {
    "tech": ["TechPulse", "GadgetHub", "CloudNine", "PixelBridge", "DataFlow"],
    "food": ["FreshBite", "TasteWorld", "SnapEats", "GourmetBox", "NomNom"],
    "auto": ["DriveForward", "AutoZen", "RoadKing", "SwiftWheels", "GreenDrive"],
    "fashion": ["StyleNest", "TrendVault", "ChicLine", "UrbanThread", "GlowWear"],
    "finance": ["WealthPath", "SafeVault", "GrowFunds", "TrustBank", "PrimeSave"],
    "travel": ["WanderLux", "AirNomad", "TripStar", "RoamFree", "SkyBound"],
    "health": ["VitaCore", "FitPulse", "NaturaMed", "WellPath", "ClearMind"],
    "gaming": ["PlayVerse", "LevelUp", "PixelRealm", "ArenaX", "QuestHub"],
}

# Global name pools organized by country.
# Used to generate diverse, internationally representative user profiles.
COUNTRIES = [
    "USA", "India", "Japan", "Brazil", "UK",
    "Germany", "South Korea", "Mexico", "Nigeria", "France",
    "Australia", "China",
]

# Sampling weights — rough streaming platform audience proportions.
COUNTRY_WEIGHTS = [0.22, 0.18, 0.08, 0.08, 0.07, 0.06, 0.07, 0.06, 0.05, 0.05, 0.04, 0.04]

COUNTRY_LANGUAGE_MAP: dict[str, list[str]] = {
    "USA":         ["English"],
    "UK":          ["English"],
    "Australia":   ["English"],
    "Nigeria":     ["English"],
    "Germany":     ["German", "English"],
    "France":      ["French", "English"],
    "Japan":       ["Japanese", "English"],
    "South Korea": ["Korean", "English"],
    "India":       ["Hindi", "English"],
    "Brazil":      ["Portuguese", "English"],
    "Mexico":      ["Spanish", "English"],
    "China":       ["Mandarin", "English"],
}

COUNTRY_NAME_POOLS: dict[str, dict[str, list[str]]] = {
    "USA": {
        "first": ["Alex", "Jordan", "Morgan", "Taylor", "Casey", "Riley", "Avery", "Quinn",
                  "Blake", "Cameron", "Dana", "Devon", "Emery", "Finley", "Hayden", "Logan"],
        "last":  ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller",
                  "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"],
    },
    "India": {
        "first": ["Priya", "Rahul", "Ananya", "Vikram", "Neha", "Arjun", "Pooja", "Rohan",
                  "Divya", "Karan", "Aisha", "Samir", "Shruti", "Aarav", "Kavya", "Ishaan"],
        "last":  ["Sharma", "Patel", "Singh", "Kumar", "Gupta", "Verma", "Joshi",
                  "Mehta", "Shah", "Nair", "Reddy", "Iyer", "Pillai", "Rao"],
    },
    "Japan": {
        "first": ["Yuki", "Haruto", "Aiko", "Kenji", "Sakura", "Ryo", "Nana",
                  "Takeshi", "Hana", "Sora", "Mizuki", "Ren", "Kaito", "Yui"],
        "last":  ["Tanaka", "Suzuki", "Watanabe", "Ito", "Yamamoto", "Nakamura",
                  "Kobayashi", "Kato", "Sato", "Abe", "Hayashi", "Yamada"],
    },
    "Brazil": {
        "first": ["Lucas", "Ana", "Pedro", "Beatriz", "Gabriel", "Mariana", "Rafael",
                  "Juliana", "Mateus", "Camila", "Felipe", "Larissa", "Guilherme", "Isabela"],
        "last":  ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Ferreira",
                  "Costa", "Rodrigues", "Alves", "Pereira", "Carvalho", "Melo"],
    },
    "UK": {
        "first": ["Oliver", "Amelia", "Harry", "Isla", "George", "Poppy", "Charlie",
                  "Daisy", "Jack", "Freya", "Alfie", "Ellie", "Archie", "Rosie"],
        "last":  ["Brown", "Smith", "Wilson", "Davies", "Evans", "Thomas",
                  "Roberts", "Walker", "White", "Hall", "Clarke", "Lewis"],
    },
    "Germany": {
        "first": ["Lukas", "Emma", "Felix", "Hannah", "Leon", "Sophie", "Jonas",
                  "Lena", "Maximilian", "Laura", "Elias", "Mia", "Noah", "Lea"],
        "last":  ["Mueller", "Schmidt", "Schneider", "Fischer", "Weber",
                  "Meyer", "Wagner", "Becker", "Schulz", "Hoffman", "Koch", "Bauer"],
    },
    "South Korea": {
        "first": ["Jimin", "Soyeon", "Junho", "Yuna", "Minjun", "Chaeyeon",
                  "Seojun", "Jisoo", "Hyunwoo", "Naeun", "Daehyun", "Seoyeon", "Taehyun"],
        "last":  ["Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho",
                  "Yoon", "Lim", "Han", "Oh", "Shin"],
    },
    "Mexico": {
        "first": ["Miguel", "Sofia", "Carlos", "Valentina", "Diego", "Isabella",
                  "Alejandro", "Camila", "Juan", "Fernanda", "Jorge", "Lucia", "Andres"],
        "last":  ["Garcia", "Martinez", "Rodriguez", "Lopez", "Hernandez",
                  "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres", "Flores", "Cruz"],
    },
    "Nigeria": {
        "first": ["Emeka", "Amara", "Chidi", "Ngozi", "Tobechukwu", "Adaeze",
                  "Kelechi", "Chisom", "Uche", "Nneka", "Obinna", "Ifunanya", "Ifeoma"],
        "last":  ["Okafor", "Adeyemi", "Nwosu", "Eze", "Obi", "Adeleke",
                  "Anyanwu", "Abubakar", "Musa", "Ibrahim", "Okonkwo", "Nwachukwu"],
    },
    "France": {
        "first": ["Pierre", "Marie", "Louis", "Sophie", "Hugo", "Lea", "Nathan",
                  "Camille", "Lucas", "Manon", "Antoine", "Chloe", "Mathieu", "Inès"],
        "last":  ["Dubois", "Martin", "Bernard", "Moreau", "Laurent",
                  "Simon", "Michel", "Thomas", "Lefevre", "Roux", "Fontaine", "Girard"],
    },
    "Australia": {
        "first": ["Liam", "Olivia", "Noah", "Charlotte", "William", "Amelia",
                  "Jack", "Isla", "Cooper", "Chloe", "Archie", "Matilda", "Angus", "Ruby"],
        "last":  ["Smith", "Jones", "Williams", "Brown", "Wilson",
                  "Taylor", "Anderson", "Thomas", "White", "Harris", "Martin", "Thompson"],
    },
    "China": {
        "first": ["Wei", "Fang", "Yang", "Jing", "Hao", "Xia", "Ming",
                  "Ling", "Tao", "Yan", "Bo", "Mei", "Jun", "Lei"],
        "last":  ["Wang", "Li", "Zhang", "Liu", "Chen", "Yang",
                  "Huang", "Zhao", "Wu", "Zhou", "Xu", "Sun"],
    },
}
