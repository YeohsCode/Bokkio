// Disposable native controls for scrolling, mutation and action verification.
internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        using var form = new Form { Text = "Bokkio interactions", AccessibleName = "Bokkio interactions", ClientSize = new Size(820, 650) };
        var search = new TextBox { AccessibleName = "Search", Location = new Point(10, 10), Width = 260 };
        var readOnly = new TextBox { AccessibleName = "Read only", Text = "fixed", ReadOnly = true, Location = new Point(290, 10) };
        var status = new Label { AccessibleName = "Result", Text = "Ready", Location = new Point(10, 42), Width = 650 };
        var submit = new Button { Text = "Submit", Location = new Point(410, 8) };
        submit.Click += (_, _) => { status.Text = "Submitted: " + search.Text; status.AccessibleName = status.Text; };
        var combo = new ComboBox { AccessibleName = "Mode", Location = new Point(10, 75), DropDownStyle = ComboBoxStyle.DropDownList };
        combo.Items.AddRange(new object[] { "First", "Second", "Third" }); combo.SelectedIndex = 0;
        var tree = new TreeView { AccessibleName = "Folders", Location = new Point(10, 110), Size = new Size(200, 120) };
        tree.Nodes.Add(new TreeNode("Parent", new TreeNode[] { new("Child") }));
        var peers = new Panel { AccessibleName = "Peers", Location = new Point(240, 75), Size = new Size(550, 155) };
        Button MakePeer(string tag, int y) {
            var button = new Button { Text = "Duplicate", AccessibleName = "Duplicate", Tag = tag, Location = new Point(10, y), Width = 130 };
            button.Click += (_, _) => { status.Text = "Peer: " + button.Tag; status.AccessibleName = status.Text; };
            return button;
        }
        peers.Controls.Add(MakePeer("A", 10)); peers.Controls.Add(MakePeer("B", 50));
        var reorder = new Button { Text = "Reorder", Location = new Point(400, 110) };
        reorder.Click += (_, _) => { peers.Controls.SetChildIndex(peers.Controls[0], 1); };
        var rebuild = new Button { Text = "Rebuild", Location = new Point(520, 110) };
        rebuild.Click += (_, _) => { var old = peers.Controls[0]; int y = old.Top; string tag = (string)old.Tag!; peers.Controls.Remove(old); old.Dispose(); peers.Controls.Add(MakePeer(tag, y)); };
        var content = new Panel { AccessibleName = "Scroll content", AutoScroll = true, Location = new Point(10, 250), Size = new Size(780, 360) };
        for (int i = 0; i < 30; i++) content.Controls.Add(new Button { Text = $"Content {i + 1}", AccessibleName = $"Content {i + 1}", Location = new Point((i % 5) * 300, (i / 5) * 150), Size = new Size(120, 40) });
        form.Controls.AddRange(new Control[] { search, readOnly, status, submit, combo, tree, peers, reorder, rebuild, content });
        // Win32 owner-data list: native controls request row text on demand.
        using var virtualWindow = new Form { Text = "Bokkio virtual rows", AccessibleName = "Bokkio virtual rows", ClientSize = new Size(380, 300) };
        var virtualList = new ListView { AccessibleName = "Virtual rows", Dock = DockStyle.Fill, View = View.Details, VirtualMode = true, VirtualListSize = 1000 };
        virtualList.Columns.Add("Row", 320);
        virtualList.RetrieveVirtualItem += (_, e) => e.Item = new ListViewItem($"Virtual {e.ItemIndex + 1}");
        virtualWindow.Controls.Add(virtualList);
        form.Shown += (_, _) => virtualWindow.Show();
        Application.Run(form);
    }
}
