// A disposable native UIA tree with a controlled number of content controls.
internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        int count = args.Length == 1 ? int.Parse(args[0]) : 50;
        if (count is not (50 or 100 or 300 or 1000))
            throw new ArgumentOutOfRangeException(nameof(count));
        Application.EnableVisualStyles();
        using var form = new Form
        {
            Text = $"Bokkio scale {count}",
            AccessibleName = $"Bokkio scale {count}",
            ClientSize = new Size(900, 700),
        };
        var panel = new FlowLayoutPanel
        {
            AccessibleName = "Scale content",
            Dock = DockStyle.Fill,
            AutoScroll = true,
        };
        var status = new Label { Text = "Ready", AccessibleName = "Ready", Dock = DockStyle.Bottom, Height = 25 };
        panel.SuspendLayout();
        for (int i = 1; i <= count; i++)
        {
            string name = $"Sample {i}";
            var button = new Button
            {
                Text = name,
                AccessibleName = name,
                Size = new Size(100, 25),
                TabStop = false,
            };
            button.Click += (_, _) => { status.Text = "Activated " + name; status.AccessibleName = status.Text; };
            panel.Controls.Add(button);
        }
        panel.ResumeLayout();
        form.Controls.Add(panel);
        form.Controls.Add(status);
        Application.Run(form);
    }
}
