using System.Runtime.InteropServices;
using System.Text.Json;

// All business controls are painted in one client surface. There are no
// Button/TextBox child controls, AutomationIds or hidden accessibility labels.
sealed class VisualForm : Form
{
    readonly string evidence;
    readonly string mode;
    string input = "";
    bool inputFocused;
    int clicks;
    static readonly Rectangle InputBox = new(60, 110, 340, 48);
    static readonly Rectangle SubmitBox = new(60, 190, 200, 52);
    [DllImport("user32.dll")] static extern bool SetWindowDisplayAffinity(IntPtr hwnd, uint affinity);

    public VisualForm(string evidence, string mode)
    {
        this.evidence = evidence; this.mode = mode;
        Text = "Bokkio visual capture fixture";
        StartPosition = FormStartPosition.Manual; Location = new Point(100, 90);
        ClientSize = new Size(640, 360); BackColor = Color.White;
        FormBorderStyle = FormBorderStyle.FixedSingle; MaximizeBox = false;
        DoubleBuffered = true; KeyPreview = true;
        Shown += (_, _) => {
            if (mode == "protected" && !SetWindowDisplayAffinity(Handle, 0x11))
                throw new InvalidOperationException("Could not set fixture capture protection");
            WriteState();
            if (mode == "minimized") WindowState = FormWindowState.Minimized;
        };
        MouseDown += (_, e) => {
            inputFocused = InputBox.Contains(e.Location);
            if (SubmitBox.Contains(e.Location)) clicks++;
            WriteState(); Invalidate();
        };
        KeyPress += (_, e) => {
            if (!inputFocused || char.IsControl(e.KeyChar)) return;
            input += e.KeyChar; WriteState(); Invalidate();
        };
    }
    void WriteState() => File.WriteAllText(evidence, JsonSerializer.Serialize(new {
        pid = Environment.ProcessId, hwnd = Handle.ToInt64(), dpi = DeviceDpi,
        width = ClientSize.Width, height = ClientSize.Height,
        origin = PointToScreen(Point.Empty), clicks, input, mode,
        internal_control_count = Controls.Count
    }));
    protected override void WndProc(ref Message message)
    {
        // A deliberately unresponsive WM_PRINT is isolated by the caller's
        // capture worker timeout, without blocking Bokkio's parent process.
        if (mode == "hang" && (message.Msg == 0x0317 || message.Msg == 0x0318))
            Thread.Sleep(30000);
        base.WndProc(ref message);
    }
    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e); var g = e.Graphics;
        using var font = new Font("Segoe UI", 18);
        g.DrawString("Bokkio native visual test", font, Brushes.Black, 60, 40);
        g.FillRectangle(Brushes.AliceBlue, InputBox); g.DrawRectangle(Pens.Black, InputBox);
        g.DrawString(input.Length == 0 ? "Enter code" : input, font, Brushes.Black, 68, 118);
        g.FillRectangle(Brushes.RoyalBlue, SubmitBox);
        g.DrawString("Run check", font, Brushes.White, 72, 200);
        g.DrawString($"Clicks: {clicks}", font, Brushes.Black, 60, 275);
        (Color color, int x, int y)[] marks = [
            (Color.FromArgb(161,11,206),8,8),
            (Color.FromArgb(19,203,101),ClientSize.Width-24,8),
            (Color.FromArgb(211,50,33),8,ClientSize.Height-24),
            (Color.FromArgb(36,104,172),ClientSize.Width-24,ClientSize.Height-24)];
        foreach (var mark in marks) { using var brush = new SolidBrush(mark.color); g.FillRectangle(brush,mark.x,mark.y,16,16); }
    }
}

static class Program
{
    [STAThread] static void Main(string[] args)
    {
        if (args.Length != 2) throw new ArgumentException("Expected evidence path and mode");
        Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        using var form = new VisualForm(args[0], args[1]);
        if (args[1] == "multiple") {
            var sibling = new VisualForm(args[0] + ".sibling.json", "normal");
            sibling.Location = new Point(800, 90); form.Shown += (_, _) => sibling.Show();
        }
        Application.Run(form);
    }
}
