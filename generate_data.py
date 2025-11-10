#!/usr/bin/env python3
"""Generate realistic health program data using LLM."""

import sys
from datetime import date, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generators import generate_all_data
from utils import save_json


def main():
    """Generate and save all data."""
    # Use start date 30 days from now to ensure fresh data
    start_date = date.today() + timedelta(days=30)

    print(f"📅 Scheduling horizon: {start_date} to {start_date + timedelta(days=90)}\n")

    # Generate all data in batches to avoid token limits
    print("🤖 Generating health program data with Gemini 2.5 Pro...\n")

    from generators import DataGenerator
    generator = DataGenerator()

    # Generate activities in smaller batches to avoid cutoff (30 per batch)
    # Pass id_offset to ensure unique IDs across batches
    print("1️⃣  Generating activities (batch 1/4)...")
    activities_batch1, cost1 = generator.generate_activities(30, start_date, id_offset=0)

    print("\n1️⃣  Generating activities (batch 2/4)...")
    activities_batch2, cost2 = generator.generate_activities(30, start_date, id_offset=30)

    print("\n1️⃣  Generating activities (batch 3/4)...")
    activities_batch3, cost2b = generator.generate_activities(30, start_date, id_offset=60)

    print("\n1️⃣  Generating activities (batch 4/4)...")
    activities_batch4, cost2c = generator.generate_activities(25, start_date, id_offset=90)

    all_activities = activities_batch1 + activities_batch2 + activities_batch3 + activities_batch4
    print(f"\n✓ Total activities generated: {len(all_activities)}")

    # Generate other data
    print("\n2️⃣  Generating specialists...")
    specialists, cost3 = generator.generate_specialists(15)

    print("\n3️⃣  Generating equipment...")
    equipment, cost4 = generator.generate_equipment(10, start_date)

    print("\n4️⃣  Generating travel periods...")
    travel, cost5 = generator.generate_travel_periods(6, start_date)

    total_cost = generator.total_cost

    data = {
        "activities": all_activities,
        "specialists": specialists,
        "equipment": equipment,
        "travel": travel
    }

    # Save to files
    output_dir = Path("data/generated")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Saving data to {output_dir}/...")
    save_json(data["activities"], output_dir / "activities.json")
    save_json(data["specialists"], output_dir / "specialists.json")
    save_json(data["equipment"], output_dir / "equipment.json")
    save_json(data["travel"], output_dir / "travel.json")

    # Save metadata
    metadata = {
        "start_date": str(start_date),
        "end_date": str(start_date + timedelta(days=90)),
        "generation_date": str(date.today()),
        "counts": {
            "activities": len(data["activities"]),
            "specialists": len(data["specialists"]),
            "equipment": len(data["equipment"]),
            "travel": len(data["travel"])
        },
        "total_cost_usd": round(total_cost, 4)
    }
    save_json(metadata, output_dir / "metadata.json")

    print(f"   ✓ activities.json ({len(data['activities'])} items)")
    print(f"   ✓ specialists.json ({len(data['specialists'])} items)")
    print(f"   ✓ equipment.json ({len(data['equipment'])} items)")
    print(f"   ✓ travel.json ({len(data['travel'])} items)")
    print(f"   ✓ metadata.json")

    print(f"\n🎉 Success! Total cost: ${total_cost:.4f}")

    if total_cost > 1.50:
        print(f"⚠️  Warning: Cost ${total_cost:.4f} exceeds target of $1.50")
    else:
        print(f"✅ Cost ${total_cost:.4f} is within budget ($1.50 target)")


if __name__ == "__main__":
    main()
