// Only the current page has native controls. This is pagination, not a
// VirtualizedItemPattern implementation: the other rows do not exist in UIA.
internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        using var form = new Form { Text = "Bokkio paged rows", AccessibleName = "Bokkio paged rows", ClientSize = new Size(660, 550) };
        var page = new TextBox { AccessibleName = "Page", Text = "1", Location = new Point(10, 10), Width = 60 };
        var go = new Button { Text = "Go", Location = new Point(80, 8) };
        var previous = new Button { Text = "Previous", Location = new Point(170, 8) };
        var next = new Button { Text = "Next", Location = new Point(260, 8) };
        var range = new Label { Location = new Point(10, 45), Width = 630 };
        var status = new Label { Text = "No row activated", AccessibleName = "No row activated", Location = new Point(10, 72), Width = 630 };
        var rows = new Panel { AccessibleName = "Current page rows", Location = new Point(10, 105), Size = new Size(640, 430) };
        int current = 1;
        void ShowPage(int number)
        {
            current = Math.Clamp(number, 1, 40);
            page.Text = current.ToString();
            foreach (Control old in rows.Controls.Cast<Control>().ToArray()) { rows.Controls.Remove(old); old.Dispose(); }
            int first = (current - 1) * 25 + 1;
            for (int offset = 0; offset < 25; offset++)
            {
                int index = first + offset;
                var button = new Button { Text = $"Row {index}", Location = new Point((offset % 5) * 126, (offset / 5) * 80), Size = new Size(115, 60) };
                button.Click += (_, _) => { status.Text = $"Activated Row {index}"; status.AccessibleName = status.Text; };
                rows.Controls.Add(button);
            }
            range.Text = $"Page {current} of 40: rows {first} to {first + 24}";
            range.AccessibleName = range.Text;
            previous.Enabled = current > 1; next.Enabled = current < 40;
        }
        go.Click += (_, _) => { if (int.TryParse(page.Text, out int number)) ShowPage(number); };
        previous.Click += (_, _) => ShowPage(current - 1);
        next.Click += (_, _) => ShowPage(current + 1);
        form.Controls.AddRange(new Control[] { page, go, previous, next, range, status, rows });
        ShowPage(1);
        Application.Run(form);
    }
}
