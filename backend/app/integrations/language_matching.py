# Shared by admin_mapping_client (KAM) and cs_assignment_client (CS) — both
# round-robin within whichever admins serve the astrologer's language(s).
def split_languages(language: str) -> list[str]:
    # Astrologer.language sometimes holds several, sheet-style: "Hindi, Telugu".
    return [part.strip() for part in language.split(",") if part.strip()]
