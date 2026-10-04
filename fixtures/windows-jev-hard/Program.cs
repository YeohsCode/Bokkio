// Disposable native UIA controls for parent context, replacement and deep trees.
internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        using var form = new Form { Text = "Bokkio Jev hard", AccessibleName = "Bokkio Jev hard", ClientSize = new Size(720, 600) };
        var status = new Label { Text = "Ready", AccessibleName = "Ready", Location = new Point(10, 10), Width = 650 };
        void Report(string text) { status.Text = text; status.AccessibleName = text; }
        Panel Pane(string name, int x) {
            var pane = new Panel { AccessibleName = name, Location = new Point(x, 45), Size = new Size(200, 70) };
            var button = new Button { Text = "Action", AccessibleName = "Action", Location = new Point(10, 10) };
            button.Click += (_, _) => Report("Clicked " + name);
            pane.Controls.Add(button); return pane;
        }
        var dynamic = new Panel { AccessibleName = "Dynamic items", Location = new Point(260, 150), Size = new Size(400, 200) };
        void Populate(string prefix) {
            foreach (Control control in dynamic.Controls.Cast<Control>().ToArray()) { dynamic.Controls.Remove(control); control.Dispose(); }
            for (int i = 1; i <= 3; i++) {
                string label = prefix + " " + i;
                var button = new Button { Text = label, AccessibleName = label, Location = new Point(10, i * 40) };
                button.Click += (_, _) => Report("Clicked " + label);
                dynamic.Controls.Add(button);
            }
        }
        Populate("Old");
        var refresh = new Button { Text = "Refresh", Location = new Point(260, 120) };
        refresh.Click += (_, _) => { Populate("Fresh"); Report("Items refreshed"); };
        var tree = new TreeView { AccessibleName = "Workflow folders", Location = new Point(10, 130), Size = new Size(230, 430) };
        var root = new TreeNode("Workflow"); tree.Nodes.Add(root);
        var parent = root;
        for (int i = 1; i <= 5; i++) { var child = new TreeNode("Level " + i); parent.Nodes.Add(child); parent = child; }
        parent.Nodes.Add(new TreeNode("Leaf"));
        tree.AfterSelect += (_, e) => Report("Selected " + e.Node!.Text);
        form.Controls.AddRange(new Control[] { status, Pane("Left pane", 10), Pane("Right pane", 260), refresh, dynamic, tree });
        Application.Run(form);
    }
}
