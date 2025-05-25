from database import SessionLocal
from database.models import Applicant, FraudPattern, EligibilityRule, ClaimHistory
from sqlalchemy.inspection import inspect
import numpy as np

OUTPUT_FILE = "database/db_dump.txt"

def print_table_schema(model, f):
    f.write(f"\nSchema for {model.__tablename__}:\n")
    for column in inspect(model).columns:
        f.write(f"  {column.name}: {column.type}\n")

def print_table_data(db, model, output_file):
    """Print all data from a table, excluding the embedding column."""
    print(f"\n{'='*80}", file=output_file)
    print(f"Data in {model.__name__} table:", file=output_file)
    print(f"{'='*80}", file=output_file)
    
    # Get all records
    records = db.query(model).all()
    
    if not records:
        print("No records found.", file=output_file)
        return
    
    # Get column names excluding 'embedding'
    columns = [c.name for c in model.__table__.columns if c.name != 'embedding']
    
    # Print column headers
    header = " | ".join(columns)
    print(header, file=output_file)
    print("-" * len(header), file=output_file)
    
    # Print each record
    for record in records:
        values = []
        for col in columns:
            value = getattr(record, col)
            if isinstance(value, (list, np.ndarray)):
                values.append(f"[{len(value)} values]")
            else:
                values.append(str(value))
        print(" | ".join(values), file=output_file)
    
    print(f"\nTotal records: {len(records)}", file=output_file)

def check_database_contents():
    with open(OUTPUT_FILE, "w") as f:
        with SessionLocal() as db:
            for model in [Applicant, FraudPattern, EligibilityRule, ClaimHistory]:
                print_table_schema(model, f)
                print_table_data(db, model, f)
    print(f"Database dump saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    check_database_contents() 