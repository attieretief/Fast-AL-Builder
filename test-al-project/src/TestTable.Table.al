table 50000 "Test Table"
{
    TableType = Normal;
    
    fields
    {
        field(1; "Entry No."; Integer)
        {
            DataClassification = SystemMetadata;
        }
        field(2; "Description"; Text[100])
        {
            DataClassification = CustomerContent;
        }
        field(3; "Created Date"; Date)
        {
            DataClassification = SystemMetadata;
        }
    }
    
    keys
    {
        key(PK; "Entry No.")
        {
            Clustered = true;
        }
    }
}