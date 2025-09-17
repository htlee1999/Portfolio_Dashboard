# Portfolio Data Storage

This directory contains all persistent data for the Portfolio Analysis Dashboard.

## File Structure

```
data/
├── portfolio.json          # Main portfolio holdings data
├── settings.json           # Application settings
├── backups/                # Automatic backups
│   └── portfolio_backup_YYYYMMDD_HHMMSS.json
├── exports/                # CSV exports
│   └── portfolio_export_YYYYMMDD_HHMMSS.csv
└── README.md              # This file
```

## Data Formats

### portfolio.json
```json
{
  "last_updated": "2024-01-15T10:30:00",
  "holdings": [
    {
      "Symbol": "AAPL",
      "Quantity": 10.0,
      "Purchase_Price": 150.0,
      "Purchase_Date": "2024-01-01",
      "Currency": "USD"
    }
  ]
}
```

### settings.json
```json
{
  "base_currency": "USD",
  "last_updated": "2024-01-15T10:30:00"
}
```

## CRUD Operations

The application provides full CRUD (Create, Read, Update, Delete) operations:

- **Create**: Add new holdings via Portfolio Builder
- **Read**: Load data on application startup
- **Update**: Modify existing holdings or settings
- **Delete**: Remove holdings or clear all data

## Backup and Export

- **Automatic Backups**: Created when using the backup function
- **CSV Exports**: Generated for external analysis
- **JSON Format**: Human-readable and easily portable

## Data Persistence

All data is automatically saved when:
- Adding new holdings
- Removing holdings
- Changing settings
- Clearing portfolio

The data persists between application sessions and is stored locally on your machine.
