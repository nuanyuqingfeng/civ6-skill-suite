using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using System.Windows.Media.Media3D;
using Firaxis.Granny;
using Firaxis.Utility;
using NexusBuddy.FileOps;
using NexusBuddy.GrannyInfos;
using NexusBuddy.GrannyWrappers;

namespace NexusBuddy;

public class CivNexusSixApplicationForm : Form
{
	public static CivNexusSixApplicationForm form;

	public static IGrannyFile loadedFile;

	public static string applicationName = "CivNexus6";

	public static int major_version = 1;

	public static int minor_version = 3;

	public static int sub_minor_version = 3;

	public string modelTemplateFilename;

	public string modelTemplateFilename2;

	public string modelTemplateFilename3;

	public string dummyWigFilename;

	public string sourceTemplatePath = "E:\\mod\\3D\\templates\\";

	private Random rand = new Random();

	private List<string> TempFiles = new List<string>();

	private IContainer components;

	private SplitContainer masterSplitContainer;

	private PropertyGrid properties;

	private ColumnHeader animation;

	private ColumnHeader duration;

	private ColumnHeader materialTypeColumnHeader;

	private ColumnHeader materialNameColumnHeader;

	private GroupBox fileInfoGroupBox;

	private RichTextBox fileInfoTextBox;

	private Label headerFilenameLabel;

	private SplitContainer leftHandSplitContainer;

	private TabControl mainTabControl;

	private TabPage editModelTabPage;

	private TabPage editMaterialsTabPage;

	private SplitContainer editModelContainer;

	private SplitContainer editMaterialsContainer;

	private Panel mainButtonPanel;

	private Button openButton;

	private Button viewButton;

	private Button saveButton;

	private Button saveAsButton;

	private Button saveAnimationButton;

	public ListView meshList;

	public ListViewWithComboBox triangleGroupsList;

	private ColumnHeader MeshNameColumnHeader;

	private ColumnHeader MaterialColumnHeader;

	private ColumnHeader TriangleGroupCountColumnHeader;

	private ColumnHeader TriangleGroupColumnHeader;

	private SplitContainer materialListPanelContainer;

	public ListView materialList;

	private ColumnHeader materialNameHeader;

	private ColumnHeader materialTypeHeader;

	private Panel materialButtonsPanel;

	private Button addMaterialButton;

	private Button deleteMaterialButton;

	private Button clearMaterialsButton;

	private TabControl animationsTabControl;

	private TabPage grannyAnimsTabPage;

	private ListView animList;

	private ColumnHeader anim;

	private ColumnHeader timeSlice;

	private Panel panel1;

	private ToolTip viewButtonToolTip;

	private TabPage otherActionsTabPage;

	private Button exportAllModelsButton;

	private Button processTextureButton;

	private Button processTexturesInDirButton;

	private Button batchConversionButton;

	private Button exportCurrentModelButton;

	private Button br2ImportButton;

	private Button openFBXButton;

	private Button overwriteBR2Button;

	private Button overwriteMeshesButton;

	private TabPage selectModelTabPage;

	private TabPage furtherActionsTabPage;

	private ListView modelList;

	private ColumnHeader modelName;

	private ListViewItem lastModelListItemChecked;

	private Button writeGeoFileButton;

	private int currentModelIndex;

	private RadioButton importExportFormatBR2NB2RadioButton;

	private RadioButton importExportFormatCN6RadioButton;

	private Label vertexFormatLabel;

	private Label importExportFiletypesLabel;

	private Button removeAnimationsButton;

	private Button removeNamedBoneButton;

	private Button resaveAllFBXAsAnimsButton;

	private Button makeTemplateButton;

	private Button exportBR2Button;

	private Label rescaleFactorLabel;

	private Label xPositionLabel;

	private Label yPositionLabel;

	private Label zPositionLabel;

	private Button insertAdjustmentBoneButton;

	private TextBox rescaleFactorTextBox;

	private TextBox xPositionTextBox;

	private TextBox yPositionTextBox;

	private TextBox zPositionTextBox;

	private ComboBox bonesComboBox;

	private Label rescaleBoneNameLabel;

	private Button rescaleNamedBoneButton;

	private Button exportNA2Button;

	private Label endTimeTextBoxLabel;

	private Label startTimeTextBoxLabel;

	private Label textureClassLabel;

	private TextBox endTimeTextBox;

	private Label angleLabel;

	private Label axisLabel;

	private ComboBox axisComboBox;

	private Label geoClassNameLabel;

	private Label materialClassNameLabel;

	private Label assetClassNameLabel;

	private Label dsgLabel;

	private Label multiModelAssetCheckBoxLabel;

	private ComboBox geoClassNameComboBox;

	private ComboBox materialClassNameComboBox;

	private ComboBox assetClassNameComboBox;

	private ComboBox dsgComboBox;

	private ComboBox vertexFormatComboBox;

	private ComboBox textureClassComboBox;

	private TextBox angleTextBox;

	private Button concatenateNA2Button;

	private Label fpsLevel;

	private TextBox fpsTextBox;

	private Button openBR2Button;

	private Label nodeLabel;

	private TextBox nodeTextBox;

	private Button loadStringDatabaseButton;

	private TextBox startTimeTextBox;

	private CheckBox multiModelAssetCheckBox;

	public CivNexusSixApplicationForm()
	{
		form = this;
		InitializeComponent();
		Available.Startup(applicationName);
		Context.Add(new GrannyContext());
		Context.Add(new ProjectConfig());
		Context.Get<GrannyContext>();
		Assembly executingAssembly = Assembly.GetExecutingAssembly();
		try
		{
			Stream manifestResourceStream = executingAssembly.GetManifestResourceStream("NexusBuddy.GrannyTemplates.model_template.fgx");
			modelTemplateFilename = Path.GetTempPath() + "modelTemplate.temp.fgx";
			FileStream fileStream = File.Create(modelTemplateFilename);
			ReadWriteStream(manifestResourceStream, fileStream);
			fileStream.Close();
			manifestResourceStream = executingAssembly.GetManifestResourceStream("NexusBuddy.GrannyTemplates.model_template_2uv.fgx");
			modelTemplateFilename2 = Path.GetTempPath() + "modelTemplate_2uv.temp.fgx";
			fileStream = File.Create(modelTemplateFilename2);
			ReadWriteStream(manifestResourceStream, fileStream);
			fileStream.Close();
			manifestResourceStream = executingAssembly.GetManifestResourceStream("NexusBuddy.GrannyTemplates.model_template_3uv.fgx");
			modelTemplateFilename3 = Path.GetTempPath() + "modelTemplate_3uv.temp.fgx";
			fileStream = File.Create(modelTemplateFilename3);
			ReadWriteStream(manifestResourceStream, fileStream);
			fileStream.Close();
			manifestResourceStream = executingAssembly.GetManifestResourceStream("NexusBuddy.GrannyTemplates.dummy.wig");
			dummyWigFilename = Path.GetTempPath() + "dummy.temp.wig";
			fileStream = File.Create(dummyWigFilename);
			ReadWriteStream(manifestResourceStream, fileStream);
			fileStream.Close();
		}
		catch (Exception)
		{
		}
	}

	private void ReadWriteStream(Stream readStream, Stream writeStream)
	{
		int num = 256;
		byte[] buffer = new byte[num];
		for (int num2 = readStream.Read(buffer, 0, num); num2 > 0; num2 = readStream.Read(buffer, 0, num))
		{
			writeStream.Write(buffer, 0, num2);
		}
		readStream.Close();
		writeStream.Close();
	}

	protected override void OnClosing(CancelEventArgs e)
	{
		CleardownAllData();
		base.OnClosing(e);
	}

	private void CleardownAllData()
	{
		loadedFile = null;
		foreach (string tempFile in TempFiles)
		{
			try
			{
				File.Delete(tempFile);
			}
			catch (Exception)
			{
			}
		}
	}

	private void AddAnimToListbox(IGrannyAnimation grannyAnimation)
	{
		animList.Items.Add(grannyAnimation.Name);
		animList.Items[animList.Items.Count - 1].SubItems.Add(grannyAnimation.Duration.ToString("f6", CultureInfo.InvariantCulture));
		animList.Items[animList.Items.Count - 1].SubItems.Add(grannyAnimation.TimeStep.ToString("f6", CultureInfo.InvariantCulture));
	}

	private void AddMeshToListbox(IGrannyMesh grannyMesh)
	{
		meshList.Items.Add(grannyMesh.Name);
		meshList.Items[meshList.Items.Count - 1].SubItems.Add(grannyMesh.TriangleMaterialGroups.Count.ToString());
		meshList.Items[meshList.Items.Count - 1].Tag = grannyMesh;
	}

	private void AddMaterialToListbox(IGrannyMaterial material)
	{
		materialList.Items.Add(material.Name);
		materialList.Items[materialList.Items.Count - 1].SubItems.Add(material.typeName);
		materialList.Items[materialList.Items.Count - 1].Tag = new MaterialProperties(material);
	}

	private void RefreshAppDataWithMessage(string message)
	{
		RefreshAppData();
		fileInfoTextBox.Text += message;
	}

	public void RefreshAppData()
	{
		string text = "";
		if (loadedFile != null)
		{
			if (currentModelIndex == -1)
			{
				currentModelIndex = 0;
			}
			materialList.Items.Clear();
			meshList.Items.Clear();
			animList.Items.Clear();
			triangleGroupsList.Items.Clear();
			properties.SelectedObject = null;
			if (loadedFile.Models.Count > 0 && loadedFile.Models[currentModelIndex].Skeleton != null)
			{
				IGrannySkeleton skeleton = loadedFile.Models[currentModelIndex].Skeleton;
				bonesComboBox.Items.Clear();
				foreach (IGrannyBone bone in skeleton.Bones)
				{
					bonesComboBox.Items.Add(bone.Name);
				}
			}
			if (modelList.Items.Count != loadedFile.Models.Count)
			{
				foreach (IGrannyModel model in loadedFile.Models)
				{
					modelList.Items.Add(model.Name);
				}
				modelList.Items[currentModelIndex].Checked = true;
			}
			if (loadedFile.Models.Count > 0)
			{
				foreach (IGrannyMesh meshBinding in loadedFile.Models[currentModelIndex].MeshBindings)
				{
					AddMeshToListbox(meshBinding);
				}
			}
			if (meshList.Items.Count > 0)
			{
				meshList.Items[0].Selected = true;
				meshList.Select();
			}
			foreach (IGrannyMaterial material in loadedFile.Materials)
			{
				AddMaterialToListbox(material);
			}
			foreach (IGrannyAnimation animation in loadedFile.Animations)
			{
				AddAnimToListbox(animation);
			}
			IGrannyFile grannyFile = loadedFile;
			string fileName = Path.GetFileName(grannyFile.Filename);
			headerFilenameLabel.Text = fileName;
			text = text + "Models: " + grannyFile.Models.Count + "     ";
			if (grannyFile.Models.Count > 0)
			{
				text = text + "Current Model: " + grannyFile.Models[currentModelIndex].Name + " (Index:" + currentModelIndex + ")" + Environment.NewLine;
				text = text + "Bones (Current Model): " + grannyFile.Models[currentModelIndex].Skeleton.Bones.Count + "     ";
				text = text + "Meshes (Current Model): " + grannyFile.Models[currentModelIndex].MeshBindings.Count + "     ";
			}
			text = text + "Meshes (Total): " + grannyFile.Meshes.Count + Environment.NewLine;
			text = text + "Materials: " + grannyFile.Materials.Count + Environment.NewLine;
			text = text + "Animations: " + grannyFile.Animations.Count + Environment.NewLine;
		}
		fileInfoTextBox.Text = text;
	}

	private void InsertAdjustmentBoneClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("Must have model file loaded to add bone.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
		}
		else
		{
			InsertAdjustmentBoneAction();
		}
	}

	private void InsertAdjustmentBoneAction()
	{
		GrannySkeletonWrapper grannySkeletonWrapper = new GrannySkeletonWrapper(loadedFile.Models[currentModelIndex].Skeleton);
		GrannySkeletonInfo grannySkeletonInfo = grannySkeletonWrapper.readSkeletonInfo();
		foreach (GrannyBoneInfo bone in grannySkeletonInfo.bones)
		{
			bone.parentIndex++;
		}
		float num = 1f;
		try
		{
			num = float.Parse(rescaleFactorTextBox.Text, CultureInfo.InvariantCulture);
		}
		catch (FormatException)
		{
		}
		float num2 = 1f;
		try
		{
			num2 = float.Parse(xPositionTextBox.Text, CultureInfo.InvariantCulture);
		}
		catch (FormatException)
		{
		}
		float num3 = 1f;
		try
		{
			num3 = float.Parse(yPositionTextBox.Text, CultureInfo.InvariantCulture);
		}
		catch (FormatException)
		{
		}
		float num4 = 1f;
		try
		{
			num4 = float.Parse(zPositionTextBox.Text, CultureInfo.InvariantCulture);
		}
		catch (FormatException)
		{
		}
		Vector3D axisOfRotation = new Vector3D(1.0, 0.0, 0.0);
		if (axisComboBox.SelectedIndex == 1)
		{
			axisOfRotation = new Vector3D(0.0, 1.0, 0.0);
		}
		else if (axisComboBox.SelectedIndex == 2)
		{
			axisOfRotation = new Vector3D(0.0, 0.0, 1.0);
		}
		float num5 = 1f;
		try
		{
			num5 = float.Parse(angleTextBox.Text, CultureInfo.InvariantCulture);
		}
		catch (FormatException)
		{
		}
		Quaternion quaternion = new Quaternion(axisOfRotation, num5);
		GrannyBoneInfo grannyBoneInfo = new GrannyBoneInfo();
		int num6 = 1;
		string text = "CN6_ADJUSTMENT_BONE";
		foreach (IGrannyBone bone2 in grannySkeletonWrapper.wrappedSkeleton.Bones)
		{
			if (bone2.Name.StartsWith(text))
			{
				num6++;
			}
		}
		grannyBoneInfo.name = text + "_" + num6;
		grannyBoneInfo.parentIndex = -1;
		GrannyTransformInfo grannyTransformInfo = new GrannyTransformInfo();
		float[] position = new float[3] { num2, num3, num4 };
		float[] orientation = new float[4]
		{
			(float)quaternion.X,
			(float)quaternion.Y,
			(float)quaternion.Z,
			(float)quaternion.W
		};
		float[] scaleShear = new float[9] { num, 0f, 0f, 0f, num, 0f, 0f, 0f, num };
		float[] inverseWorldTransform = new float[16]
		{
			1f, 0f, 0f, 0f, 0f, 1f, 0f, 0f, 0f, 0f,
			1f, 0f, 0f, 0f, 0f, 1f
		};
		grannyTransformInfo.position = position;
		grannyTransformInfo.orientation = orientation;
		grannyTransformInfo.scaleShear = scaleShear;
		grannyTransformInfo.flags = 7;
		grannyBoneInfo.localTransform = grannyTransformInfo;
		grannyBoneInfo.inverseWorldTransform = inverseWorldTransform;
		grannySkeletonInfo.bones.Insert(0, grannyBoneInfo);
		grannySkeletonWrapper.writeSkeletonInfo(grannySkeletonInfo);
		SaveAction();
		RefreshAppDataWithMessage("ADJUSTMENT BONE INSERTED.");
	}

	private void RescaleNamedBoneButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("Must have model file loaded to add bone.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		GrannySkeletonWrapper grannySkeletonWrapper = new GrannySkeletonWrapper(loadedFile.Models[currentModelIndex].Skeleton);
		GrannySkeletonInfo grannySkeletonInfo = grannySkeletonWrapper.readSkeletonInfo();
		float num = float.Parse(rescaleFactorTextBox.Text, CultureInfo.InvariantCulture);
		GrannyBoneInfo grannyBoneInfo = new GrannyBoneInfo();
		grannyBoneInfo.name = string.Concat(bonesComboBox.SelectedItem, "_FX");
		grannyBoneInfo.parentIndex = bonesComboBox.SelectedIndex;
		GrannyTransformInfo grannyTransformInfo = new GrannyTransformInfo();
		float[] position = new float[3];
		float[] orientation = new float[4] { 0f, 0f, 0f, 1f };
		float[] scaleShear = new float[9] { num, 0f, 0f, 0f, num, 0f, 0f, 0f, num };
		float[] inverseWorldTransform = grannySkeletonInfo.bones[bonesComboBox.SelectedIndex].inverseWorldTransform;
		grannyTransformInfo.position = position;
		grannyTransformInfo.orientation = orientation;
		grannyTransformInfo.scaleShear = scaleShear;
		grannyTransformInfo.flags = 4;
		grannyBoneInfo.localTransform = grannyTransformInfo;
		grannyBoneInfo.inverseWorldTransform = inverseWorldTransform;
		grannySkeletonInfo.bones.Add(grannyBoneInfo);
		grannySkeletonWrapper.writeSkeletonInfo(grannySkeletonInfo);
		SaveAction();
		RefreshAppDataWithMessage("RESCALE BONE ADDED.");
	}

	private void ExportNA2ButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("Must have model file loaded to export animation.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
		}
		else
		{
			if (loadedFile == null)
			{
				return;
			}
			OpenFileDialog openFileDialog = new OpenFileDialog();
			openFileDialog.Filter = "fgx files (*.fgx) | *.fgx";
			openFileDialog.FilterIndex = 0;
			openFileDialog.RestoreDirectory = true;
			if (openFileDialog.ShowDialog() != DialogResult.OK)
			{
				return;
			}
			IGrannyFile grannyFile = OpenFileAsTempFileCopy(openFileDialog.FileName, "tempanimopen");
			if (grannyFile.Animations.Count == 1)
			{
				int num = 5;
				float timeWindowStart = -1f;
				try
				{
					timeWindowStart = float.Parse(startTimeTextBox.Text, CultureInfo.InvariantCulture);
				}
				catch (FormatException)
				{
				}
				float timeWindowEnd = -1f;
				try
				{
					timeWindowEnd = float.Parse(endTimeTextBox.Text, CultureInfo.InvariantCulture);
				}
				catch (FormatException)
				{
				}
				int fpsInput = 0;
				try
				{
					fpsInput = int.Parse(fpsTextBox.Text, CultureInfo.InvariantCulture);
				}
				catch (FormatException)
				{
				}
				int num2 = NB2NA2FileOps.exportNA2(loadedFile.Models[currentModelIndex], grannyFile.Animations[0], openFileDialog.FileName, timeWindowStart, timeWindowEnd, fpsInput, num);
				if (num2 == num)
				{
					RefreshAppDataWithMessage("ANIMATION EXPORT FAILED! Retry Count: " + num2);
				}
				else
				{
					RefreshAppDataWithMessage("ANIMATION EXPORTED! Retry Count: " + num2);
				}
			}
		}
	}

	private void ProcessTexturesInDirectoryClick(object sender, EventArgs e)
	{
		FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog
		{
			SelectedPath = Settings.Default.RecentFolder
		};
		folderBrowserDialog.ShowNewFolderButton = false;
		folderBrowserDialog.RootFolder = Environment.SpecialFolder.Desktop;
		DialogResult dialogResult = folderBrowserDialog.ShowDialog();
		string[] allowedExtensions = new string[4] { ".png", ".dds", ".tga", ".jpg" };
		if (dialogResult != DialogResult.OK)
		{
			return;
		}
		string selectedPath = folderBrowserDialog.SelectedPath;
		Settings.Default.RecentFolder = selectedPath;
		IEnumerable<string> enumerable = from s in Directory.GetFiles(selectedPath, "*.*", SearchOption.TopDirectoryOnly)
			where allowedExtensions.Contains(Path.GetExtension(s.ToLower()))
			select s;
		foreach (string item in enumerable)
		{
			string message = ProcessTextureAction(item, textureClassComboBox.Text);
			RefreshAppDataWithMessage(message);
		}
	}

	private void ProcessTextureClick(object sender, EventArgs e)
	{
		OpenFileDialog openFileDialog = new OpenFileDialog();
		openFileDialog.Filter = "Image Files (*.png;*.dds;*.tga;*.jpg)|*.png;*.dds;*.tga;*.jpg";
		openFileDialog.FilterIndex = 0;
		openFileDialog.RestoreDirectory = true;
		if (openFileDialog.ShowDialog() == DialogResult.OK)
		{
			string fileName = openFileDialog.FileName;
			string message = ProcessTextureAction(fileName, textureClassComboBox.Text);
			RefreshAppDataWithMessage(message);
		}
	}

	private string ProcessTextureAction(string filename, string textureClassName)
	{
		string fileName = Path.GetFileName(filename);
		string directoryName = Path.GetDirectoryName(filename);
		string text = directoryName + "\\Textures";
		Directory.CreateDirectory(text);
		TextureClass textureClass = TextureClass.GetAllTextureClasses()[textureClassName];
		Dictionary<string, string> imageMetadata = GetImageMetadata(directoryName, fileName);
		string text2 = "FAILED!";
		if (imageMetadata.Count != 0)
		{
			int num = int.Parse(imageMetadata["height"]);
			int num2 = int.Parse(imageMetadata["width"]);
			if (num > textureClass.MaxHeight)
			{
				MessageBox.Show("Height of input image is too high for " + textureClassName + ". Should be less than " + textureClass.MaxHeight + ".", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return "Failed";
			}
			if (num < textureClass.MinHeight)
			{
				MessageBox.Show("Height of input image is too low for " + textureClassName + ". Should be greater than " + textureClass.MinHeight + ".", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return "Failed";
			}
			if (num2 > textureClass.MaxWidth)
			{
				MessageBox.Show("Height of input image is too high for " + textureClassName + ". Should be less than " + textureClass.MaxWidth + ".", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return "Failed";
			}
			if (num2 < textureClass.MinWidth)
			{
				MessageBox.Show("Height of input image is too low for " + textureClassName + ". Should be greater than " + textureClass.MinWidth + ".", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return "Failed";
			}
			if (textureClass.RequireSquare && num2 != num)
			{
				MessageBox.Show("Input image needs to be square for " + textureClassName + ".", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				return "Failed";
			}
			ProcessStartInfo processStartInfo = new ProcessStartInfo();
			processStartInfo.CreateNoWindow = true;
			processStartInfo.UseShellExecute = false;
			processStartInfo.FileName = "texconv.exe";
			processStartInfo.RedirectStandardOutput = true;
			processStartInfo.WindowStyle = ProcessWindowStyle.Normal;
			processStartInfo.WorkingDirectory = directoryName;
			processStartInfo.Arguments = "\"" + fileName + "\" -f " + textureClass.PixelFormat + " -o \"" + text + "\" -y";
			if (!textureClass.AllowArtistMips)
			{
				processStartInfo.Arguments += " -m 1";
			}
			Process process = new Process
			{
				StartInfo = processStartInfo
			};
			process.Start();
			text2 = processStartInfo.FileName + " " + processStartInfo.Arguments + "\n";
			while (!process.StandardOutput.EndOfStream)
			{
				string text3 = process.StandardOutput.ReadLine();
				if (text3.StartsWith("reading") || text3.StartsWith("writing"))
				{
					text2 = text2 + text3 + "\n";
				}
			}
			process.Close();
			string fileNameWithoutExtension = Path.GetFileNameWithoutExtension(fileName);
			string shortFilename = fileNameWithoutExtension + ".dds";
			Dictionary<string, string> imageMetadata2 = GetImageMetadata(text, shortFilename);
			MetadataWriter.WriteTextureFile(text, Path.GetFileNameWithoutExtension(fileName), imageMetadata2, textureClassName, textureClass);
		}
		return text2;
	}

	private static Dictionary<string, string> GetImageMetadata(string path, string shortFilename)
	{
		ProcessStartInfo processStartInfo = new ProcessStartInfo();
		processStartInfo.CreateNoWindow = true;
		processStartInfo.UseShellExecute = false;
		processStartInfo.FileName = "texdiag.exe";
		processStartInfo.RedirectStandardOutput = true;
		processStartInfo.WindowStyle = ProcessWindowStyle.Normal;
		processStartInfo.WorkingDirectory = path;
		processStartInfo.Arguments = "info \"" + shortFilename + "\"";
		Process process = new Process
		{
			StartInfo = processStartInfo
		};
		process.Start();
		Dictionary<string, string> dictionary = new Dictionary<string, string>();
		while (!process.StandardOutput.EndOfStream)
		{
			string text = process.StandardOutput.ReadLine();
			if (text.Contains("="))
			{
				string[] array = text.Split('=');
				string key = array[0].Trim();
				string value = array[1].Trim();
				dictionary[key] = value;
			}
		}
		return dictionary;
	}

	private void OpenButtonClick(object sender, EventArgs e)
	{
		OpenButtonDialogAction("fgx/gr2 files (*.fgx)|*.fgx;*.gr2|br2 files (*.br2)|*.br2|cn6 files (*.cn6)|*.cn6|All files (*.*)|*.*");
	}

	private void OpenFBXButtonClick(object sender, EventArgs e)
	{
		if (string.IsNullOrEmpty(nodeTextBox.Text))
		{
			MessageBox.Show("Must specify Node for FBX import!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
		}
		else
		{
			OpenButtonDialogAction("FBX files (*.fbx)|*.fbx|All files (*.*)|*.*");
		}
	}

	private void OpenBR2ButtonClick(object sender, EventArgs e)
	{
		OpenButtonDialogAction("br2 files (*.br2)|*.br2|All files (*.*)|*.*");
	}

	private void OpenCN6ButtonClick(object sender, EventArgs e)
	{
		OpenButtonDialogAction("cn6 files (*.cn6)|*.cn6|All files (*.*)|*.*");
	}

	private void OpenButtonDialogAction(string filterString)
	{
		OpenFileDialog openFileDialog = new OpenFileDialog();
		openFileDialog.Filter = filterString;
		openFileDialog.FilterIndex = 0;
		openFileDialog.RestoreDirectory = true;
		if (openFileDialog.ShowDialog() == DialogResult.OK)
		{
			string fileName = openFileDialog.FileName;
			currentModelIndex = -1;
			modelList.Items.Clear();
			loadedFile = OpenFileAction(fileName);
			RefreshAppDataWithMessage("FILE OPENED: " + fileName);
		}
	}

	public IGrannyFile OpenFileAction(string openFilename)
	{
		IGrannyFile grannyFile = OpenFileAsTempFileCopy(openFilename, "tempopen");
		bool flag = false;
		if (openFilename.ToLower().Contains(".fbx"))
		{
			openFilename = openFilename.Replace(".fbx", ".fgx");
			openFilename = openFilename.Replace(".FBX", ".fgx");
			flag = true;
		}
		else if (openFilename.ToLower().Contains(".br2"))
		{
			openFilename = openFilename.Replace(".br2", ".fgx");
			openFilename = openFilename.Replace(".BR2", ".fgx");
		}
		else if (openFilename.ToLower().Contains(".cn6"))
		{
			openFilename = openFilename.Replace(".cn6", ".fgx");
			openFilename = openFilename.Replace(".CN6", ".fgx");
		}
		else if (openFilename.ToLower().Contains(".gr2"))
		{
			openFilename = openFilename.Replace(".gr2", ".fgx");
			openFilename = openFilename.Replace(".GR2", ".fgx");
			flag = true;
		}
		grannyFile.Filename = openFilename;
		if (flag)
		{
			grannyFile.Save();
		}
		return grannyFile;
	}

	public static string GetVersionString()
	{
		return major_version + "." + minor_version + "." + sub_minor_version;
	}

	public static void SetExporterInfo(GrannyFileWrapper fileWrapper)
	{
		fileWrapper.setExporterInfo(applicationName, major_version, minor_version, sub_minor_version, 0);
	}

	public IGrannyFile OpenFileAsTempFileCopy(string openFilename, string prefix)
	{
		GrannyContext grannyContext = Context.Get<GrannyContext>();
		string tempPath = Path.GetTempPath();
		string text = tempPath + prefix;
		string nodeName = "Root";
		if (openFilename.ToLower().Contains(".fbx"))
		{
			if (!string.IsNullOrEmpty(nodeTextBox.Text))
			{
				nodeName = nodeTextBox.Text;
			}
			string tempFilename = text;
			tempFilename = AppendRandomNumberAndFGXExtension(tempFilename);
			FBXImporter.ImportFBXFile(openFilename, tempFilename, nodeName);
			IGrannyFile grannyFile = grannyContext.LoadGrannyFile(tempFilename);
			GrannyFileWrapper grannyFileWrapper = new GrannyFileWrapper(grannyFile);
			grannyFileWrapper.setNumMaterials(0);
			text = AppendRandomNumberAndFGXExtension(text);
			SaveAsAction(grannyFile, text, updateAppDataAndSaveMessage: false);
			TempFiles.Add(text);
			TempFiles.Add(tempFilename);
		}
		else if (openFilename.ToLower().Contains(".br2"))
		{
			text = AppendRandomNumberAndFGXExtension(text);
			BR2FileOps.importBR2(openFilename, text, grannyContext);
			TempFiles.Add(text);
		}
		else if (openFilename.ToLower().Contains(".cn6"))
		{
			text = AppendRandomNumberAndFGXExtension(text);
			CN6FileOps.importCN6(openFilename, text, grannyContext, vertexFormatComboBox.SelectedIndex);
			TempFiles.Add(text);
		}
		else
		{
			text = AppendRandomNumberAndFGXExtension(text);
			TempFiles.Add(text);
			try
			{
				if (File.Exists(text))
				{
					File.Delete(text);
				}
			}
			catch (Exception)
			{
			}
			File.Copy(openFilename, text);
		}
		IGrannyFileLoader grannyFileLoader = new GrannyFileLoader();
		return grannyFileLoader.LoadGrannyFile(text);
	}

	private string FindRootString(List<string> strings)
	{
		if (strings.Count > 0)
		{
			string text = strings.First();
			strings.Remove(text);
			foreach (string @string in strings)
			{
				char[] array = text.ToCharArray();
				char[] array2 = @string.ToCharArray();
				List<char> list = new List<char>();
				for (int i = 0; i < array2.Length && i < array.Length; i++)
				{
					if (array2[i].Equals(array[i]))
					{
						list.Add(array2[i]);
					}
				}
				text = new string(list.ToArray());
			}
			return text.TrimEnd('_');
		}
		return "no_animations";
	}

	private void BatchConversionAction(object sender, EventArgs e)
	{
		OpenFileDialog openFileDialog = new OpenFileDialog();
		openFileDialog.Filter = "dat files (*.dat) | *.dat";
		openFileDialog.FilterIndex = 0;
		openFileDialog.RestoreDirectory = true;
		if (openFileDialog.ShowDialog() != DialogResult.OK)
		{
			return;
		}
		string fileName = openFileDialog.FileName;
		string directoryName = Path.GetDirectoryName(fileName);
		string text = directoryName + "\\Modbuddy";
		Directory.CreateDirectory(text);
		StreamReader streamReader = new StreamReader(fileName);
		string pattern = "(.*);(.*);(.*);(.*)";
		RefreshAppDataWithMessage("Batch conversion start!");
		while (!streamReader.EndOfStream)
		{
			string input = streamReader.ReadLine();
			Regex regex = new Regex(pattern);
			MatchCollection matchCollection = regex.Matches(input);
			foreach (Match item2 in matchCollection)
			{
				string text2 = item2.Groups[1].Value.Trim().ToLower();
				string text3 = text2.Replace(".gr2", "");
				string value = item2.Groups[2].Value;
				string value2 = item2.Groups[3].Value;
				string text4 = item2.Groups[4].Value.Trim();
				bool flag = text4.Length > 0;
				List<string> list = new List<string>();
				HashSet<string> hashSet = new HashSet<string>();
				string item = directoryName + "\\" + text3 + ".cn6";
				List<string> list2 = new List<string>();
				list2.AddRange(Directory.GetFiles(directoryName, text3 + "__*.cn6"));
				if (list2.Count == 0)
				{
					list2.Add(item);
				}
				List<IGrannyFile> list3 = new List<IGrannyFile>();
				List<Dictionary<string, string>> list4 = new List<Dictionary<string, string>>();
				Dictionary<string, string> civ6ShortNameToLongNameLookup = null;
				bool flag2 = false;
				if (list2.Count > 1)
				{
					flag2 = true;
				}
				list2.RemoveAll((string x) => x.Contains("_batch.cn6"));
				foreach (string item3 in list2)
				{
					string fileName2 = Path.GetFileName(item3);
					string text5 = fileName2.Replace(".cn6", "");
					string text6 = assetClassNameComboBox.Text;
					string className = geoClassNameComboBox.Text;
					string materialClass = materialClassNameComboBox.Text;
					string textureClassName = textureClassComboBox.Text;
					string text7 = dsgComboBox.Text;
					RefreshAppDataWithMessage("Processing " + text5 + "...");
					string text8 = directoryName + "\\" + text5;
					if (!flag)
					{
						text4 = text5;
					}
					string[] array = value.Split(',');
					string[] array2 = value2.Split(',');
					List<string> list5 = new List<string>();
					Directory.CreateDirectory(text8);
					string text9 = text8 + "\\" + text5 + ".cn6";
					File.Copy(item3, text9, overwrite: true);
					List<string> list6 = new List<string>();
					if (fileName2.ToLower().Contains("float"))
					{
						int num = 0;
						num++;
					}
					string[] array3 = array;
					foreach (string text10 in array3)
					{
						if (text10.Length > 4)
						{
							string text11 = directoryName + "\\" + text10;
							string text12 = text8 + "\\" + text10.ToLower();
							if (File.Exists(text11))
							{
								File.Copy(text11, text12, overwrite: true);
								list6.Add(text12.ToLower());
							}
							list5.Add(text10.Replace(".gr2", ""));
						}
					}
					string text13 = null;
					if (list5.Count.Equals(1))
					{
						string[] array4 = text5.Split('_');
						if (array4.Length > 1)
						{
							text13 = array4[0];
						}
					}
					if (text13 == null)
					{
						text13 = FindRootString(list5);
					}
					List<string> list7 = new List<string>();
					string[] array5 = array2;
					foreach (string text14 in array5)
					{
						string text15 = text14.Replace(".tga", ".dds");
						string text16 = directoryName + "\\" + text15;
						string text17 = text8 + "\\" + text15;
						if (File.Exists(text16))
						{
							File.Copy(text16, text17.ToLower(), overwrite: true);
							list7.Add(text17.ToLower());
						}
					}
					loadedFile = OpenFileAction(text9);
					SaveAction();
					InsertAdjustmentBoneAction();
					if (text9.Contains("_DCL_"))
					{
						className = "DecalGeometry";
						materialClass = "DecalMaterial";
						textureClassName = "Decal_BaseColor";
					}
					MetadataWriter.WriteGeoAnimFile(loadedFile, currentModelIndex, className);
					list3.Add(loadedFile);
					string text18 = text8 + "\\Materials";
					Directory.CreateDirectory(text18);
					List<string> list8 = new List<string>();
					List<string> list9 = new List<string>();
					Dictionary<string, string> dictionary = new Dictionary<string, string>();
					foreach (IGrannyMaterial material in loadedFile.Materials)
					{
						string name = material.Name;
						string text19 = material.Name;
						if (text19.Contains("."))
						{
							string[] array6 = text19.Split('.');
							text19 = array6[0];
						}
						string text20 = text19;
						string[] array7 = array2;
						foreach (string text21 in array7)
						{
							if (text21.StartsWith(text19))
							{
								text20 = text21.Replace(".tga", ".dds").Replace(".dds", "");
								dictionary.Add(name, text20);
								break;
							}
						}
						if (!list8.Contains(text20) && text20.Length > 0)
						{
							MetadataWriter.WriteMaterialFile(text18, text20 + ".mtl", text20, materialClass, tintMask: false);
							list8.Add(text20);
						}
						list9.Add(text20.ToLower());
					}
					string text22 = text8 + "\\Geometries";
					Directory.CreateDirectory(text22);
					string fileName3 = Path.GetFileName(text9.Replace(".cn6", ".fgx"));
					File.Copy(text8 + "\\" + fileName3, text22 + "\\" + fileName3, overwrite: true);
					string fileName4 = Path.GetFileName(text9.Replace(".cn6", ".geo"));
					File.Copy(text8 + "\\" + fileName4, text22 + "\\" + fileName4, overwrite: true);
					string outputDirectory = "Animations";
					civ6ShortNameToLongNameLookup = BuildShortNameToLongNameLookup(text13, array);
					if (loadedFile != null && (!flag2 || !multiModelAssetCheckBox.Checked))
					{
						MetadataWriter.WriteAssetFile(loadedFile, civ6ShortNameToLongNameLookup, text6, text7, text4, new List<Dictionary<string, string>> { dictionary });
					}
					list4.Add(dictionary);
					if (list5.Count() > 0)
					{
						ResaveAnimationGR2FilesToOutputDirectory(text8, outputDirectory, array);
					}
					CleardownAllData();
					foreach (string item4 in list6)
					{
						File.Delete(item4);
						File.Delete(item4.Replace(".gr2", ".fgx"));
					}
					TextInfo textInfo = new CultureInfo("en-US", useUserOverride: false).TextInfo;
					string text23 = textInfo.ToTitleCase(text4) + ".ast";
					string text24 = text8 + "\\Assets";
					Directory.CreateDirectory(text24);
					if (!flag2 || !multiModelAssetCheckBox.Checked)
					{
						File.Copy(text8 + "\\" + text23, text24 + "\\" + text23, overwrite: true);
					}
					hashSet = new HashSet<string>(list7);
					foreach (string item5 in hashSet)
					{
						string fileNameWithoutExtension = Path.GetFileNameWithoutExtension(item5);
						if (list9.Contains(fileNameWithoutExtension) && !list.Contains(fileNameWithoutExtension))
						{
							ProcessTextureAction(item5, textureClassName);
							list.Add(fileNameWithoutExtension);
						}
					}
					File.Delete(text8 + "\\" + fileName3);
					File.Delete(text8 + "\\" + fileName4);
					File.Delete(text8 + "\\" + text23);
					File.Delete(text9);
					string text25 = text8;
					string newValue = text;
					string[] directories = Directory.GetDirectories(text25, "*", SearchOption.AllDirectories);
					foreach (string text26 in directories)
					{
						Directory.CreateDirectory(text26.Replace(text25, newValue));
					}
					string[] files = Directory.GetFiles(text25, "*.*", SearchOption.AllDirectories);
					foreach (string text27 in files)
					{
						File.Copy(text27, text27.Replace(text25, newValue), overwrite: true);
					}
					Directory.Delete(text8, recursive: true);
				}
				foreach (string item6 in hashSet.ToList())
				{
					string path = item6.Replace(".tga", ".dds");
					string fileNameWithoutExtension2 = Path.GetFileNameWithoutExtension(path);
					string text28 = text + "\\" + Path.GetFileName(path);
					if (File.Exists(text28))
					{
						if (!list.Contains(fileNameWithoutExtension2))
						{
							ProcessTextureAction(text28, textureClassComboBox.Text);
						}
						File.Delete(text28);
					}
				}
				if (flag2 && multiModelAssetCheckBox.Checked)
				{
					string assetsDirectory = text + "\\Assets";
					MetadataWriter.WriteMultiModelAssetFile(assetsDirectory, text3, list3, civ6ShortNameToLongNameLookup, assetClassNameComboBox.Text, dsgComboBox.Text, null, list4);
				}
			}
		}
		RefreshAppDataWithMessage("Batch conversion complete!");
	}

	private string AppendRandomNumberAndFGXExtension(string tempFilename)
	{
		tempFilename += rand.Next(1000000);
		tempFilename += rand.Next(1000000);
		tempFilename += rand.Next(1000000);
		tempFilename += ".fgx";
		return tempFilename;
	}

	private void ViewButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("No file is currently loaded.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
		}
		else
		{
			ViewAction();
		}
	}

	private void ViewAction()
	{
		ProcessStartInfo processStartInfo = new ProcessStartInfo();
		processStartInfo.CreateNoWindow = false;
		processStartInfo.UseShellExecute = false;
		processStartInfo.FileName = "fgxviewer.exe";
		processStartInfo.WindowStyle = ProcessWindowStyle.Normal;
		if (loadedFile != null)
		{
			processStartInfo.Arguments = "\"" + loadedFile.Filename + "\"";
			Process.Start(processStartInfo);
		}
	}

	private void SaveAsButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("No file is currently loaded.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		SaveFileDialog saveFileDialog = new SaveFileDialog();
		saveFileDialog.Filter = "fgx files (*.fgx)|*.fgx|All files (*.*)|*.*";
		saveFileDialog.FilterIndex = 0;
		saveFileDialog.RestoreDirectory = true;
		if (saveFileDialog.ShowDialog() == DialogResult.OK)
		{
			string fileName = saveFileDialog.FileName;
			SaveAsAction(loadedFile, fileName, updateAppDataAndSaveMessage: true);
		}
	}

	private void SaveButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("No file is currently loaded.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		DialogResult dialogResult = DialogResult.Yes;
		if (File.Exists(loadedFile.Filename))
		{
			dialogResult = MessageBox.Show("Are you sure you want to overwrite this file?", "Warning!", MessageBoxButtons.YesNo, MessageBoxIcon.Exclamation);
		}
		if (dialogResult == DialogResult.Yes)
		{
			SaveAction();
		}
	}

	public void SaveAction()
	{
		string filename = loadedFile.Filename;
		SaveAsAction(loadedFile, filename, updateAppDataAndSaveMessage: true);
	}

	public IGrannyFile SaveAsAction(IGrannyFile fileToSave, string fileName, bool updateAppDataAndSaveMessage)
	{
		GrannyFileWrapper exporterInfo = new GrannyFileWrapper(fileToSave);
		SetExporterInfo(exporterInfo);
		string sourceFileName = (fileToSave.Filename = fileName.Replace(".fgx", "_temp_" + rand.Next(1000000) + rand.Next(1000000) + ".fgx"));
		fileToSave.Source = "Tool";
		fileToSave.Save();
		if (File.Exists(fileName))
		{
			File.Delete(fileName);
		}
		File.Move(sourceFileName, fileName);
		fileToSave.Filename = fileName;
		GrannyContext grannyContext = Context.Get<GrannyContext>();
		string tempPath = Path.GetTempPath();
		string text2 = tempPath + "tempopen";
		text2 += rand.Next(1000000);
		text2 += rand.Next(1000000);
		text2 += ".fgx";
		TempFiles.Add(text2);
		File.Copy(fileName, text2);
		IGrannyFile grannyFile = grannyContext.LoadGrannyFile(text2);
		grannyFile.Filename = fileName;
		grannyFile.Source = "Tool";
		loadedFile = grannyFile;
		modelList.Items.Clear();
		if (updateAppDataAndSaveMessage)
		{
			RefreshAppDataWithMessage("FILE SAVED: " + fileName);
		}
		return loadedFile;
	}

	public string GetApplicationNameWithVersionNumber()
	{
		return applicationName + " " + GetVersionString();
	}

	private string getShortFilenameForLoadedFile()
	{
		return Path.GetFileName(loadedFile.Filename);
	}

	private void SaveAnimationClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("No file is currently loaded.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		SaveFileDialog saveFileDialog = new SaveFileDialog();
		saveFileDialog.Filter = "fgx files (*.fgx)|*.fgx|All files (*.*)|*.*";
		saveFileDialog.FilterIndex = 0;
		saveFileDialog.RestoreDirectory = true;
		saveFileDialog.FileName = getShortFilenameForLoadedFile().Replace(".fgx", "_anim.fgx");
		if (saveFileDialog.ShowDialog() == DialogResult.OK)
		{
			string fileName = saveFileDialog.FileName;
			SaveAnimationsAction(loadedFile, fileName);
			RefreshAppDataWithMessage("ANIMATION FILE SAVED.");
		}
	}

	private static List<IGrannyFile> SaveAnimationsAction(IGrannyFile grannyFile, string filename)
	{
		GrannyContext grannyContext = Context.Get<GrannyContext>();
		int num = 0;
		List<IGrannyFile> list = new List<IGrannyFile>();
		foreach (IGrannyAnimation animation in grannyFile.Animations)
		{
			string text = "";
			if (num > 0)
			{
				text = string.Concat(num);
			}
			IGrannyFile grannyFile2 = grannyContext.CreateEmptyGrannyFile(filename.Replace(".fgx", text + ".fgx"));
			grannyFile2.AddAnimationReference(animation);
			grannyFile2.AddArtToolAndExporterReference(grannyFile);
			grannyFile2.Save();
			list.Add(grannyFile2);
			num++;
		}
		return list;
	}

	private void OverwriteMeshesButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("You need to open a file before you can overwrite meshes!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		GrannyContext grannyContext = Context.Get<GrannyContext>();
		OpenFileDialog openFileDialog = new OpenFileDialog();
		if (importExportFormatBR2NB2RadioButton.Checked)
		{
			openFileDialog.Filter = "br2 files (*.br2)|*.br2";
		}
		else
		{
			openFileDialog.Filter = "cn6 files (*.cn6)|*.cn6";
		}
		openFileDialog.FilterIndex = 0;
		openFileDialog.RestoreDirectory = true;
		if (openFileDialog.ShowDialog() == DialogResult.OK)
		{
			string fileName = openFileDialog.FileName;
			if (importExportFormatBR2NB2RadioButton.Checked)
			{
				BR2FileOps.overwriteMeshes(loadedFile, fileName, grannyContext, currentModelIndex);
			}
			else
			{
				CN6FileOps.overwriteMeshes(loadedFile, fileName, grannyContext, currentModelIndex, vertexFormatComboBox.SelectedIndex);
			}
			RefreshAppDataWithMessage("MESHES OVERWRITTEN from " + fileName);
		}
	}

	private void OverwriteMeshesButtonCN6Click(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("You need to open a file before you can overwrite meshes!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		GrannyContext grannyContext = Context.Get<GrannyContext>();
		OpenFileDialog openFileDialog = new OpenFileDialog();
		openFileDialog.Filter = "cn6 files (*.cn6)|*.cn6";
		openFileDialog.FilterIndex = 0;
		openFileDialog.RestoreDirectory = true;
		if (openFileDialog.ShowDialog() == DialogResult.OK)
		{
			string fileName = openFileDialog.FileName;
			CN6FileOps.overwriteMeshes(loadedFile, fileName, grannyContext, currentModelIndex, vertexFormatComboBox.SelectedIndex);
			RefreshAppDataWithMessage("MESHES OVERWRITTEN from " + fileName);
		}
	}

	private void ConvertParticlePSBClick(object sender, EventArgs e)
	{
		OpenFileDialog openFileDialog = new OpenFileDialog();
		openFileDialog.Filter = "psb files (*.psb)|*.psb";
		openFileDialog.FilterIndex = 0;
		openFileDialog.RestoreDirectory = true;
		HashSet<string> hashSet = new HashSet<string>();
		HashSet<string> hashSet2 = new HashSet<string>();
		string text = "blank";
		if (openFileDialog.ShowDialog() == DialogResult.OK)
		{
			text = openFileDialog.FileName;
			string input = File.ReadAllText(text, Encoding.ASCII);
			MatchCollection matchCollection = Regex.Matches(input, "([a-zA-Z0-9._]+)");
			foreach (Match item in matchCollection)
			{
				string text2 = item.ToString();
				if (text2.Length > 4)
				{
					if (text2.Contains("."))
					{
						hashSet2.Add(item.ToString());
					}
					else if (text2.Contains("_"))
					{
						hashSet.Add(item.ToString());
					}
				}
			}
		}
		using (TextWriter textWriter = new StreamWriter(text + ".txs", append: false))
		{
			foreach (string item2 in hashSet2)
			{
				textWriter.WriteLine(item2);
			}
		}
		using TextWriter textWriter2 = new StreamWriter(text + ".mts", append: false);
		foreach (string item3 in hashSet)
		{
			textWriter2.WriteLine(item3);
		}
	}

	private void RemoveNamedBoneButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("Must have model file loaded to remove bone.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
		}
		else if (MessageBox.Show("Are you sure you want to delete the selected bone? There is no undo.", "Warning!", MessageBoxButtons.YesNo, MessageBoxIcon.Exclamation) == DialogResult.Yes)
		{
			GrannySkeletonWrapper grannySkeletonWrapper = new GrannySkeletonWrapper(loadedFile.Models[currentModelIndex].Skeleton);
			GrannySkeletonInfo grannySkeletonInfo = grannySkeletonWrapper.readSkeletonInfo();
			int selectedIndex = bonesComboBox.SelectedIndex;
			grannySkeletonInfo.bones.RemoveAt(selectedIndex);
			grannySkeletonWrapper.writeSkeletonInfo(grannySkeletonInfo);
			SaveAction();
			RefreshAppDataWithMessage("BONE REMOVED.");
		}
	}

	private void RemoveAnimationsButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("No file is currently loaded.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		GrannyFileWrapper grannyFileWrapper = new GrannyFileWrapper(loadedFile);
		grannyFileWrapper.setNumAnimations(0);
		grannyFileWrapper.setNumTrackGroups(0);
		SaveAction();
	}

	private void ConcatenateNA2ButtonClick(object sender, EventArgs e)
	{
		FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog
		{
			SelectedPath = Settings.Default.RecentFolder
		};
		folderBrowserDialog.ShowNewFolderButton = false;
		folderBrowserDialog.RootFolder = Environment.SpecialFolder.Desktop;
		DialogResult dialogResult = folderBrowserDialog.ShowDialog();
		if (dialogResult != DialogResult.OK)
		{
			return;
		}
		string text = "combined" + rand.Next(100000) + ".na2";
		Settings.Default.RecentFolder = folderBrowserDialog.SelectedPath;
		IEnumerable<string> enumerable = from s in Directory.GetFiles(folderBrowserDialog.SelectedPath, "*.*", SearchOption.TopDirectoryOnly)
			where s.ToLower().EndsWith(".na2")
			select s;
		TextWriter textWriter = new StreamWriter(text);
		textWriter.WriteLine("// Animation NA2 - Exported from " + GetApplicationNameWithVersionNumber());
		int num = 0;
		foreach (string item in enumerable)
		{
			if (item.LastIndexOf("__") > 0)
			{
				num++;
			}
		}
		textWriter.WriteLine("FrameSets: " + num);
		string text2 = null;
		foreach (string item2 in enumerable)
		{
			if (item2.LastIndexOf("__") <= 0)
			{
				continue;
			}
			text2 = item2.Substring(0, item2.LastIndexOf("__")) + ".na2";
			StreamReader streamReader = new StreamReader(item2);
			while (streamReader.Peek() >= 0)
			{
				string text3 = streamReader.ReadLine();
				if (!text3.StartsWith("//") && !text3.StartsWith("FrameSets"))
				{
					textWriter.Write(text3 + "\n");
				}
			}
			streamReader.Close();
		}
		textWriter.Close();
		if (File.Exists(text2))
		{
			File.Delete(text2);
		}
		if (File.Exists(text))
		{
			File.Copy(text, text2);
			File.Delete(text);
		}
		RefreshAppDataWithMessage("NA2 FILES CONCATENATED.");
	}

	private void ResaveAllGR2FilesInDirAsAnimsClick(object sender, EventArgs e)
	{
		FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog
		{
			SelectedPath = Settings.Default.RecentFolder
		};
		folderBrowserDialog.ShowNewFolderButton = false;
		folderBrowserDialog.RootFolder = Environment.SpecialFolder.Desktop;
		DialogResult dialogResult = folderBrowserDialog.ShowDialog();
		if (dialogResult == DialogResult.OK)
		{
			string selectedPath = folderBrowserDialog.SelectedPath;
			Settings.Default.RecentFolder = selectedPath;
			IEnumerable<string> enumerable = from s in Directory.GetFiles(selectedPath, "*.*", SearchOption.TopDirectoryOnly)
				where s.ToLower().EndsWith(".gr2")
				select s;
			string outputDirectory = "fgx_anm_output";
			if (loadedFile != null)
			{
				string fileNameWithoutExtension = Path.GetFileNameWithoutExtension(loadedFile.Filename);
				Dictionary<string, string> civ6ShortNameToLongNameLookup = BuildShortNameToLongNameLookup(fileNameWithoutExtension, enumerable);
				MetadataWriter.WriteAssetFile(loadedFile, civ6ShortNameToLongNameLookup, assetClassNameComboBox.Text, dsgComboBox.Text, null, null);
			}
			ResaveAnimationGR2FilesToOutputDirectory(selectedPath, outputDirectory, enumerable);
			CleardownAllData();
			RefreshAppDataWithMessage("ALL GR2 FILES IN DIRECTORY SAVED AS .fgx/.anm");
		}
	}

	private static Dictionary<string, string> BuildShortNameToLongNameLookup(string animationRoot, IEnumerable<string> filenamesList)
	{
		List<string> list = new List<string>();
		foreach (string filenames in filenamesList)
		{
			list.Add(Path.GetFileNameWithoutExtension(filenames).ToLower());
		}
		Dictionary<string, List<string>> civ6ToCiv5ShortNameLookup = GetCiv6ToCiv5ShortNameLookup();
		Dictionary<string, string> dictionary = new Dictionary<string, string>();
		Dictionary<string, string> dictionary2 = new Dictionary<string, string>();
		foreach (string key in civ6ToCiv5ShortNameLookup.Keys)
		{
			List<string> list2 = civ6ToCiv5ShortNameLookup[key];
			foreach (string item in list2)
			{
				if (!dictionary.Keys.Contains(item))
				{
					foreach (string item2 in list)
					{
						if (item2.Equals((animationRoot + item).ToLower()))
						{
							dictionary.Add(item, item2);
							break;
						}
					}
				}
				if (dictionary.ContainsKey(item))
				{
					dictionary2.Add(key, dictionary[item]);
					break;
				}
			}
		}
		return dictionary2;
	}

	private string FindFileInFolderList(IEnumerable<string> folderList, string filename)
	{
		try
		{
			foreach (string folder in folderList)
			{
				string text = folder + "\\" + filename;
				if (File.Exists(text))
				{
					return text;
				}
			}
		}
		catch (Exception)
		{
			return null;
		}
		return null;
	}

	private void ResaveAnimationGR2FilesToOutputDirectory(string selectedPath, string outputDirectory, IEnumerable<string> files)
	{
		Directory.CreateDirectory(selectedPath + "\\" + outputDirectory);
		string item = "D:\\mod\\Civ5Unpacks\\UnitModels_All\\resaveBatch\\";
		List<string> folderList = new List<string> { selectedPath, item };
		foreach (string file in files)
		{
			string filename = Path.GetFileName(file).ToLower();
			string text = FindFileInFolderList(folderList, filename);
			if (text == null)
			{
				continue;
			}
			IGrannyFile grannyFile = OpenFileAction(text);
			string text2 = Path.GetFileName(text);
			if (text2.ToLower().Contains(".gr2"))
			{
				text2 = text2.Replace(".gr2", ".fgx");
				text2 = text2.Replace(".GR2", ".fgx");
			}
			string filename2 = (grannyFile.Filename = selectedPath + "\\" + outputDirectory + "\\" + text2);
			List<IGrannyFile> list = SaveAnimationsAction(grannyFile, filename2);
			foreach (IGrannyFile item2 in list)
			{
				MetadataWriter.WriteGeoAnimFile(item2, 0, geoClassNameComboBox.Text);
			}
		}
	}

	private static Dictionary<string, List<string>> GetCiv6ToCiv5ShortNameLookup()
	{
		Dictionary<string, List<string>> dictionary = new Dictionary<string, List<string>>();
		StreamReader streamReader = new StreamReader("Civ6ToCiv5AnimMap.txt");
		while (streamReader.Peek() >= 0)
		{
			string text = streamReader.ReadLine();
			string[] array = text.Split(':');
			string[] source = array[1].Split(';');
			dictionary.Add(array[0], source.ToList());
		}
		return dictionary;
	}

	private void WriteGeoFileButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("You need to open a file before you can write .geo/.anm file!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		MetadataWriter.WriteGeoAnimFile(loadedFile, currentModelIndex, geoClassNameComboBox.Text);
		RefreshAppDataWithMessage("WRITE .geo/.anm FILE COMPLETE!");
	}

	private void WriteGeometrySetDataClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("You need to open a file before you can write GeometrySet data!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		MetadataWriter.WriteGeometrySet(loadedFile, assetClassNameComboBox.Text);
		RefreshAppDataWithMessage("WRITE GeometrySet XML DATA COMPLETE!");
	}

	private void ClearMaterialsClick(object sender, EventArgs e)
	{
		if (MessageBox.Show("Are you sure you want to delete all materials? There is no undo.", "Warning!", MessageBoxButtons.YesNo, MessageBoxIcon.Exclamation) == DialogResult.Yes)
		{
			ClearMaterials();
		}
		RefreshAppData();
	}

	public void ClearMaterials()
	{
		List<ListViewItem> list = new List<ListViewItem>();
		foreach (object item in materialList.Items)
		{
			MaterialProperties materialProperties = (item as ListViewItem).Tag as MaterialProperties;
			foreach (IGrannyMesh mesh in loadedFile.Meshes)
			{
				mesh.RemoveMaterialBinding(materialProperties.GetMaterial());
			}
			loadedFile.RemoveMaterial(materialProperties.GetMaterial());
			loadedFile.Materials.Remove(materialProperties.GetMaterial());
			list.Add(item as ListViewItem);
			foreach (object item2 in meshList.Items)
			{
				if ((item2 as ListViewItem).SubItems[1].Text == materialProperties.Name)
				{
					(item2 as ListViewItem).SubItems[1].Text = "<unassigned>";
				}
			}
		}
		foreach (ListViewItem item3 in list)
		{
			materialList.Items.Remove(item3);
		}
		properties.SelectedObject = null;
	}

	private void DeleteMaterialClick(object sender, EventArgs e)
	{
		if (materialList.SelectedItems.Count > 0 && MessageBox.Show("Are you sure you want to delete the selected materials? There is no undo.", "Warning!", MessageBoxButtons.YesNo, MessageBoxIcon.Exclamation) == DialogResult.Yes)
		{
			DeletedSelectedMaterial();
		}
		RefreshAppData();
	}

	public void DeletedSelectedMaterial()
	{
		List<ListViewItem> list = new List<ListViewItem>();
		foreach (ListViewItem item in materialList.Items)
		{
			if (!item.Selected)
			{
				continue;
			}
			MaterialProperties materialProperties = item.Tag as MaterialProperties;
			foreach (IGrannyMesh mesh in loadedFile.Meshes)
			{
				mesh.RemoveMaterialBinding(materialProperties.GetMaterial());
			}
			loadedFile.RemoveMaterial(materialProperties.GetMaterial());
			loadedFile.Materials.Remove(materialProperties.GetMaterial());
			list.Add(item);
			foreach (object item2 in meshList.Items)
			{
				if ((item2 as ListViewItem).SubItems[1].Text == materialProperties.Name)
				{
					(item2 as ListViewItem).SubItems[1].Text = "<unassigned>";
				}
			}
		}
		foreach (ListViewItem item3 in list)
		{
			materialList.Items.Remove(item3);
		}
		properties.SelectedObject = null;
	}

	private void AddMaterialClick(object sender, EventArgs e)
	{
		addMaterialButton.Enabled = false;
		if (loadedFile != null)
		{
			AddNewMaterial();
			RefreshAppData();
			addMaterialButton.Enabled = true;
		}
	}

	public void AddNewMaterial()
	{
		AddNewMaterial(null);
	}

	public IGrannyMaterial AddNewMaterial(string inputMaterialName)
	{
		List<string> list = new List<string>();
		foreach (IGrannyMaterial material in loadedFile.Materials)
		{
			list.Add(material.Name);
		}
		IGrannyMaterial materialFromTemplateFile = GetMaterialFromTemplateFile();
		if (inputMaterialName != null)
		{
			materialFromTemplateFile.Name = inputMaterialName;
		}
		else
		{
			string name = "Default_Material";
			for (int i = 1; i < 1000000; i++)
			{
				string text = "Default_Material_" + i;
				if (!list.Contains(text))
				{
					name = text;
					break;
				}
			}
			materialFromTemplateFile.Name = name;
		}
		loadedFile.AddMaterialReference(materialFromTemplateFile);
		AddMaterialToListbox(materialFromTemplateFile);
		return materialFromTemplateFile;
	}

	public IGrannyMaterial GetMaterialFromTemplateFile()
	{
		if (loadedFile == null)
		{
			return null;
		}
		GrannyContext grannyContext = Context.Get<GrannyContext>();
		string tempPath = Path.GetTempPath();
		string text = tempPath + "temptemplate";
		text += rand.Next(10000000);
		text += rand.Next(10000000);
		text += rand.Next(10000000);
		text += rand.Next(10000000);
		text += ".fgx";
		TempFiles.Add(text);
		File.Copy(modelTemplateFilename, text);
		IGrannyFile grannyFile = grannyContext.LoadGrannyFile(text);
		IGrannyMaterial grannyMaterial = null;
		foreach (IGrannyMaterial material in grannyFile.Materials)
		{
			if (material.Name == "Default_Material")
			{
				grannyMaterial = material;
			}
		}
		if (grannyMaterial == null)
		{
			grannyMaterial = grannyFile.Materials[0];
		}
		return grannyMaterial;
	}

	private void ExportAllModels(object sender, EventArgs e)
	{
		if (importExportFormatBR2NB2RadioButton.Checked)
		{
			ExportNB2ButtonClick(sender, e);
		}
		else
		{
			ExportCN6ButtonClick(sender, e);
		}
	}

	private void ExportModel(object sender, EventArgs e)
	{
		if (importExportFormatBR2NB2RadioButton.Checked)
		{
			ExportNB2CurrentModelButtonClick(sender, e);
		}
		else
		{
			ExportCN6CurrentModelButtonClick(sender, e);
		}
	}

	private void ImportModel(object sender, EventArgs e)
	{
		if (importExportFormatBR2NB2RadioButton.Checked)
		{
			OpenBR2ButtonClick(sender, e);
		}
		else
		{
			OpenCN6ButtonClick(sender, e);
		}
	}

	private void ExportNB2ButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("You need to open a file before you can export to NB2!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		NB2NA2FileOps.exportAllModelsToNB2(loadedFile);
		RefreshAppDataWithMessage("EXPORT TO NB2 COMPLETE.");
	}

	private void ExportCN6ButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("You need to open a file before you can export to CN6!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		CN6FileOps.exportAllModelsToCN6(loadedFile);
		RefreshAppDataWithMessage("EXPORT TO CN6 COMPLETE.");
	}

	private void ExportNB2CurrentModelButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("You need to open a file before you can export to NB2!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		NB2NA2FileOps.exportNB2(loadedFile, currentModelIndex);
		RefreshAppDataWithMessage("EXPORT TO NB2 COMPLETE.");
	}

	private void ExportCN6CurrentModelButtonClick(object sender, EventArgs e)
	{
		if (loadedFile == null)
		{
			MessageBox.Show("You need to open a file before you can export to CN6!", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
			return;
		}
		CN6FileOps.cn6Export(loadedFile, currentModelIndex);
		RefreshAppDataWithMessage("EXPORT TO CN6 COMPLETE.");
	}

	private void MakeTemplateButtonClick(object sender, EventArgs e)
	{
		string openFilename = sourceTemplatePath + "IMP_Chateau_Main.fgx";
		IGrannyFile grannyFile = form.OpenFileAsTempFileCopy(openFilename, "tempimport");
		GrannyMeshWrapper grannyMeshWrapper = new GrannyMeshWrapper(grannyFile.Meshes[0]);
		grannyMeshWrapper.setName("BLANK_MESH");
		grannyMeshWrapper.setNumVertices(1);
		grannyMeshWrapper.setNumIndices16(1);
		grannyMeshWrapper.setGroupTriCountForIndex(0, 1);
		grannyMeshWrapper.setNumMaterialBindings(1);
		foreach (IGrannyMaterial materialBinding in grannyFile.Meshes[0].MaterialBindings)
		{
			if (materialBinding.Name == "IMP_Chateau")
			{
				GrannyMaterialWrapper grannyMaterialWrapper = new GrannyMaterialWrapper(materialBinding);
				grannyMaterialWrapper.setName("Default_Material");
			}
		}
		GrannyModelWrapper grannyModelWrapper = new GrannyModelWrapper(grannyFile.Models[0]);
		GrannySkeletonWrapper grannySkeletonWrapper = new GrannySkeletonWrapper(grannyModelWrapper.wrappedModel.Skeleton);
		grannyModelWrapper.setNumMeshBindings(1);
		grannyModelWrapper.setName("BLANK_MODEL");
		grannySkeletonWrapper.setNumBones(1);
		grannySkeletonWrapper.setName("BLANK_SKELETON");
		GrannyFileWrapper grannyFileWrapper = new GrannyFileWrapper(grannyFile);
		grannyFileWrapper.setNumMeshes(1);
		grannyFileWrapper.setNumVertexDatas(1);
		grannyFileWrapper.setNumSkeletons(1);
		grannyFileWrapper.setNumTriTopologies(1);
		grannyFileWrapper.setNumTextures(1);
		SaveAsAction(grannyFile, sourceTemplatePath + "model_template_3uv.fgx", updateAppDataAndSaveMessage: true);
	}

	public void SelectMesh(int meshIndex)
	{
		meshList.Items[meshIndex].Selected = true;
		meshList.Select();
	}

	public void SelectMaterial(int materialIndex)
	{
		materialList.Items[materialIndex].Selected = true;
		materialList.Select();
	}

	public void UpdateMaterialBindings()
	{
		if (meshList.SelectedItems.Count == 0 || meshList.SelectedItems.Count > 1)
		{
			return;
		}
		IGrannyMesh grannyMesh = meshList.SelectedItems[0].Tag as IGrannyMesh;
		int num = 0;
		for (int i = 0; i < triangleGroupsList.Items.Count; i++)
		{
			if (triangleGroupsList.Items[i].SubItems[1].Text != "<unassigned>")
			{
				num++;
			}
		}
		if (num != triangleGroupsList.Items.Count)
		{
			return;
		}
		IGrannyMaterial[] array = grannyMesh.MaterialBindings.ToArray();
		foreach (IGrannyMaterial kMaterial in array)
		{
			grannyMesh.RemoveMaterialBinding(kMaterial);
		}
		for (int k = 0; k < triangleGroupsList.Items.Count; k++)
		{
			for (int l = 0; l < loadedFile.Materials.Count; l++)
			{
				IGrannyMaterial grannyMaterial = loadedFile.Materials[l];
				string value = grannyMaterial.Name + " (" + grannyMaterial.typeName + ")";
				if (triangleGroupsList.Items[k].SubItems[1].Text.Equals(value))
				{
					grannyMesh.AddMaterialBinding(grannyMaterial);
					break;
				}
			}
		}
	}

	private void PropertiesPropertyValueChanged(object s, PropertyValueChangedEventArgs e)
	{
		if (!(e.ChangedItem.Label == "Name") || !(properties.SelectedObject is MaterialProperties))
		{
			return;
		}
		bool flag = true;
		foreach (ListViewItem item in materialList.Items)
		{
			if (item.Text == (string)e.ChangedItem.Value && properties.SelectedObject as MaterialProperties != item.Tag as MaterialProperties)
			{
				(properties.SelectedObject as MaterialProperties).Name = e.OldValue as string;
				MessageBox.Show("A material of this name already exists.", "Error!", MessageBoxButtons.OK, MessageBoxIcon.Hand);
				flag = false;
			}
		}
		if (!flag)
		{
			return;
		}
		foreach (ListViewItem item2 in materialList.Items)
		{
			if (item2.Text == (string)e.OldValue)
			{
				item2.Text = e.ChangedItem.Value as string;
			}
		}
		foreach (ListViewItem item3 in meshList.Items)
		{
			if (item3.SubItems[1].Text == (string)e.OldValue)
			{
				item3.SubItems[1].Text = e.ChangedItem.Value as string;
			}
		}
	}

	private void MeshListSelectedIndexChanged(object sender, EventArgs e)
	{
		List<object> list = new List<object>();
		if (meshList.SelectedItems.Count <= 0)
		{
			return;
		}
		foreach (object selectedItem in meshList.SelectedItems)
		{
			if ((selectedItem as ListViewItem).Tag is IGrannyMesh grannyMesh)
			{
				list.Add(grannyMesh);
				RefreshTriangleGroupsList(grannyMesh);
			}
		}
		properties.SelectedObjects = list.ToArray();
	}

	private void RefreshTriangleGroupsList(IGrannyMesh mesh)
	{
		triangleGroupsList.Items.Clear();
		for (int i = 0; i < mesh.TriangleMaterialGroups.Count; i++)
		{
			IGrannyTriMaterialGroup grannyTriMaterialGroup = mesh.TriangleMaterialGroups[i];
			triangleGroupsList.Items.Add(i.ToString() + " (" + grannyTriMaterialGroup.TriFirst + " - " + (grannyTriMaterialGroup.TriFirst + grannyTriMaterialGroup.TriCount - 1) + ")");
			if (mesh.MaterialBindings.ElementAtOrDefault(grannyTriMaterialGroup.MaterialIndex) != null)
			{
				IGrannyMaterial grannyMaterial = mesh.MaterialBindings[grannyTriMaterialGroup.MaterialIndex];
				int num = -1;
				for (int j = 0; j < loadedFile.Materials.Count; j++)
				{
					IGrannyMaterial grannyMaterial2 = loadedFile.Materials[j];
					if (grannyMaterial.Name.Equals(grannyMaterial2.Name) && grannyMaterial.typeName.Equals(grannyMaterial2.typeName))
					{
						num = j;
						break;
					}
				}
				triangleGroupsList.Items[triangleGroupsList.Items.Count - 1].SubItems.Add(grannyMaterial.Name + " (" + grannyMaterial.typeName + ")").Tag = num;
			}
			else
			{
				triangleGroupsList.Items[triangleGroupsList.Items.Count - 1].SubItems.Add("<unassigned>");
			}
		}
	}

	private void MaterialListSelectedIndexChanged(object sender, EventArgs e)
	{
		List<object> list = new List<object>();
		if (materialList.SelectedItems.Count <= 0)
		{
			return;
		}
		foreach (object selectedItem in materialList.SelectedItems)
		{
			if ((selectedItem as ListViewItem).Tag is MaterialProperties item)
			{
				list.Add(item);
			}
		}
		properties.SelectedObjects = list.ToArray();
	}

	protected override void Dispose(bool disposing)
	{
		if (disposing && components != null)
		{
			components.Dispose();
		}
		base.Dispose(disposing);
	}

	private void ModelListCheckChanged(object sender, ItemCheckEventArgs e)
	{
		SelectModel(e.Index);
	}

	public void SelectModel(int inputIndex)
	{
		int num = currentModelIndex;
		if (lastModelListItemChecked != null && lastModelListItemChecked.Checked && lastModelListItemChecked != modelList.Items[inputIndex])
		{
			lastModelListItemChecked.Checked = false;
		}
		lastModelListItemChecked = modelList.Items[inputIndex];
		currentModelIndex = lastModelListItemChecked.Index;
		if (num != currentModelIndex)
		{
			RefreshAppData();
		}
	}

	private void InitializeComponent()
	{
		this.components = new System.ComponentModel.Container();
		System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(NexusBuddy.CivNexusSixApplicationForm));
		this.masterSplitContainer = new System.Windows.Forms.SplitContainer();
		this.leftHandSplitContainer = new System.Windows.Forms.SplitContainer();
		this.mainButtonPanel = new System.Windows.Forms.Panel();
		this.openFBXButton = new System.Windows.Forms.Button();
		this.overwriteBR2Button = new System.Windows.Forms.Button();
		this.openButton = new System.Windows.Forms.Button();
		this.saveButton = new System.Windows.Forms.Button();
		this.saveAsButton = new System.Windows.Forms.Button();
		this.saveAnimationButton = new System.Windows.Forms.Button();
		this.mainTabControl = new System.Windows.Forms.TabControl();
		this.editModelTabPage = new System.Windows.Forms.TabPage();
		this.editMaterialsTabPage = new System.Windows.Forms.TabPage();
		this.editModelContainer = new System.Windows.Forms.SplitContainer();
		this.editMaterialsContainer = new System.Windows.Forms.SplitContainer();
		this.meshList = new System.Windows.Forms.ListView();
		this.triangleGroupsList = new NexusBuddy.ListViewWithComboBox();
		this.MeshNameColumnHeader = new System.Windows.Forms.ColumnHeader();
		this.MaterialColumnHeader = new System.Windows.Forms.ColumnHeader();
		this.TriangleGroupCountColumnHeader = new System.Windows.Forms.ColumnHeader();
		this.TriangleGroupColumnHeader = new System.Windows.Forms.ColumnHeader();
		this.materialListPanelContainer = new System.Windows.Forms.SplitContainer();
		this.materialList = new System.Windows.Forms.ListView();
		this.materialNameHeader = new System.Windows.Forms.ColumnHeader();
		this.materialTypeHeader = new System.Windows.Forms.ColumnHeader();
		this.materialButtonsPanel = new System.Windows.Forms.Panel();
		this.addMaterialButton = new System.Windows.Forms.Button();
		this.deleteMaterialButton = new System.Windows.Forms.Button();
		this.clearMaterialsButton = new System.Windows.Forms.Button();
		this.animationsTabControl = new System.Windows.Forms.TabControl();
		this.grannyAnimsTabPage = new System.Windows.Forms.TabPage();
		this.animList = new System.Windows.Forms.ListView();
		this.anim = new System.Windows.Forms.ColumnHeader();
		this.timeSlice = new System.Windows.Forms.ColumnHeader();
		this.otherActionsTabPage = new System.Windows.Forms.TabPage();
		this.nodeLabel = new System.Windows.Forms.Label();
		this.nodeTextBox = new System.Windows.Forms.TextBox();
		this.openBR2Button = new System.Windows.Forms.Button();
		this.fpsLevel = new System.Windows.Forms.Label();
		this.fpsTextBox = new System.Windows.Forms.TextBox();
		this.concatenateNA2Button = new System.Windows.Forms.Button();
		this.angleLabel = new System.Windows.Forms.Label();
		this.axisLabel = new System.Windows.Forms.Label();
		this.axisComboBox = new System.Windows.Forms.ComboBox();
		this.geoClassNameComboBox = new System.Windows.Forms.ComboBox();
		this.assetClassNameComboBox = new System.Windows.Forms.ComboBox();
		this.materialClassNameComboBox = new System.Windows.Forms.ComboBox();
		this.dsgComboBox = new System.Windows.Forms.ComboBox();
		this.multiModelAssetCheckBox = new System.Windows.Forms.CheckBox();
		this.vertexFormatComboBox = new System.Windows.Forms.ComboBox();
		this.endTimeTextBoxLabel = new System.Windows.Forms.Label();
		this.startTimeTextBoxLabel = new System.Windows.Forms.Label();
		this.geoClassNameLabel = new System.Windows.Forms.Label();
		this.assetClassNameLabel = new System.Windows.Forms.Label();
		this.materialClassNameLabel = new System.Windows.Forms.Label();
		this.dsgLabel = new System.Windows.Forms.Label();
		this.multiModelAssetCheckBoxLabel = new System.Windows.Forms.Label();
		this.textureClassLabel = new System.Windows.Forms.Label();
		this.endTimeTextBox = new System.Windows.Forms.TextBox();
		this.startTimeTextBox = new System.Windows.Forms.TextBox();
		this.exportNA2Button = new System.Windows.Forms.Button();
		this.exportBR2Button = new System.Windows.Forms.Button();
		this.rescaleBoneNameLabel = new System.Windows.Forms.Label();
		this.rescaleNamedBoneButton = new System.Windows.Forms.Button();
		this.bonesComboBox = new System.Windows.Forms.ComboBox();
		this.textureClassComboBox = new System.Windows.Forms.ComboBox();
		this.rescaleFactorLabel = new System.Windows.Forms.Label();
		this.insertAdjustmentBoneButton = new System.Windows.Forms.Button();
		this.angleTextBox = new System.Windows.Forms.TextBox();
		this.rescaleFactorTextBox = new System.Windows.Forms.TextBox();
		this.xPositionLabel = new System.Windows.Forms.Label();
		this.yPositionLabel = new System.Windows.Forms.Label();
		this.zPositionLabel = new System.Windows.Forms.Label();
		this.xPositionTextBox = new System.Windows.Forms.TextBox();
		this.yPositionTextBox = new System.Windows.Forms.TextBox();
		this.zPositionTextBox = new System.Windows.Forms.TextBox();
		this.makeTemplateButton = new System.Windows.Forms.Button();
		this.removeAnimationsButton = new System.Windows.Forms.Button();
		this.removeNamedBoneButton = new System.Windows.Forms.Button();
		this.resaveAllFBXAsAnimsButton = new System.Windows.Forms.Button();
		this.vertexFormatLabel = new System.Windows.Forms.Label();
		this.importExportFiletypesLabel = new System.Windows.Forms.Label();
		this.importExportFormatBR2NB2RadioButton = new System.Windows.Forms.RadioButton();
		this.importExportFormatCN6RadioButton = new System.Windows.Forms.RadioButton();
		this.writeGeoFileButton = new System.Windows.Forms.Button();
		this.exportCurrentModelButton = new System.Windows.Forms.Button();
		this.overwriteMeshesButton = new System.Windows.Forms.Button();
		this.exportAllModelsButton = new System.Windows.Forms.Button();
		this.processTextureButton = new System.Windows.Forms.Button();
		this.processTexturesInDirButton = new System.Windows.Forms.Button();
		this.batchConversionButton = new System.Windows.Forms.Button();
		this.selectModelTabPage = new System.Windows.Forms.TabPage();
		this.furtherActionsTabPage = new System.Windows.Forms.TabPage();
		this.modelList = new System.Windows.Forms.ListView();
		this.modelName = new System.Windows.Forms.ColumnHeader();
		this.panel1 = new System.Windows.Forms.Panel();
		this.headerFilenameLabel = new System.Windows.Forms.Label();
		this.viewButton = new System.Windows.Forms.Button();
		this.fileInfoGroupBox = new System.Windows.Forms.GroupBox();
		this.fileInfoTextBox = new System.Windows.Forms.RichTextBox();
		this.properties = new System.Windows.Forms.PropertyGrid();
		this.animation = new System.Windows.Forms.ColumnHeader();
		this.duration = new System.Windows.Forms.ColumnHeader();
		this.materialTypeColumnHeader = new System.Windows.Forms.ColumnHeader();
		this.materialNameColumnHeader = new System.Windows.Forms.ColumnHeader();
		this.viewButtonToolTip = new System.Windows.Forms.ToolTip(this.components);
		this.br2ImportButton = new System.Windows.Forms.Button();
		this.loadStringDatabaseButton = new System.Windows.Forms.Button();
		this.masterSplitContainer.BeginInit();
		this.masterSplitContainer.Panel1.SuspendLayout();
		this.masterSplitContainer.Panel2.SuspendLayout();
		this.masterSplitContainer.SuspendLayout();
		this.leftHandSplitContainer.BeginInit();
		this.leftHandSplitContainer.Panel1.SuspendLayout();
		this.leftHandSplitContainer.Panel2.SuspendLayout();
		this.leftHandSplitContainer.SuspendLayout();
		this.mainButtonPanel.SuspendLayout();
		this.mainTabControl.SuspendLayout();
		this.editModelTabPage.SuspendLayout();
		this.editMaterialsTabPage.SuspendLayout();
		this.editModelContainer.BeginInit();
		this.editModelContainer.Panel1.SuspendLayout();
		this.editModelContainer.SuspendLayout();
		this.editMaterialsContainer.BeginInit();
		this.editMaterialsContainer.Panel1.SuspendLayout();
		this.editMaterialsContainer.SuspendLayout();
		this.materialListPanelContainer.BeginInit();
		this.materialListPanelContainer.Panel1.SuspendLayout();
		this.materialListPanelContainer.SuspendLayout();
		this.materialButtonsPanel.SuspendLayout();
		this.animationsTabControl.SuspendLayout();
		this.grannyAnimsTabPage.SuspendLayout();
		this.otherActionsTabPage.SuspendLayout();
		this.selectModelTabPage.SuspendLayout();
		this.furtherActionsTabPage.SuspendLayout();
		this.panel1.SuspendLayout();
		this.fileInfoGroupBox.SuspendLayout();
		base.SuspendLayout();
		this.masterSplitContainer.Dock = System.Windows.Forms.DockStyle.Fill;
		this.masterSplitContainer.Location = new System.Drawing.Point(0, 0);
		this.masterSplitContainer.Name = "masterSplitContainer";
		this.masterSplitContainer.Panel1.Controls.Add(this.leftHandSplitContainer);
		this.masterSplitContainer.Panel2.Controls.Add(this.panel1);
		this.masterSplitContainer.Panel2.Controls.Add(this.fileInfoGroupBox);
		this.masterSplitContainer.Panel2.Controls.Add(this.properties);
		this.masterSplitContainer.Size = new System.Drawing.Size(1008, 618);
		this.masterSplitContainer.SplitterDistance = 492;
		this.masterSplitContainer.TabIndex = 1;
		this.leftHandSplitContainer.Dock = System.Windows.Forms.DockStyle.Fill;
		this.leftHandSplitContainer.Location = new System.Drawing.Point(0, 0);
		this.leftHandSplitContainer.Name = "leftHandSplitContainer";
		this.leftHandSplitContainer.Orientation = System.Windows.Forms.Orientation.Horizontal;
		this.leftHandSplitContainer.Panel1.Controls.Add(this.mainButtonPanel);
		this.leftHandSplitContainer.Panel2.Controls.Add(this.mainTabControl);
		this.leftHandSplitContainer.Size = new System.Drawing.Size(492, 618);
		this.leftHandSplitContainer.SplitterDistance = 42;
		this.leftHandSplitContainer.TabIndex = 2;
		this.mainButtonPanel.Controls.Add(this.openFBXButton);
		this.mainButtonPanel.Controls.Add(this.overwriteBR2Button);
		this.mainButtonPanel.Controls.Add(this.openButton);
		this.mainButtonPanel.Controls.Add(this.saveButton);
		this.mainButtonPanel.Controls.Add(this.saveAsButton);
		this.mainButtonPanel.Controls.Add(this.saveAnimationButton);
		this.mainButtonPanel.Dock = System.Windows.Forms.DockStyle.Fill;
		this.mainButtonPanel.Location = new System.Drawing.Point(0, 0);
		this.mainButtonPanel.Name = "mainButtonPanel";
		this.mainButtonPanel.Size = new System.Drawing.Size(492, 42);
		this.mainButtonPanel.TabIndex = 9;
		this.openFBXButton.Location = new System.Drawing.Point(155, 5);
		this.openFBXButton.Name = "openFBXButton";
		this.openFBXButton.Size = new System.Drawing.Size(87, 33);
		this.openFBXButton.TabIndex = 7;
		this.openFBXButton.Text = "Import";
		this.openFBXButton.UseVisualStyleBackColor = true;
		this.openFBXButton.Click += new System.EventHandler(ImportModel);
		this.overwriteBR2Button.Location = new System.Drawing.Point(67, 5);
		this.overwriteBR2Button.Name = "overwriteBR2Button";
		this.overwriteBR2Button.Size = new System.Drawing.Size(82, 33);
		this.overwriteBR2Button.TabIndex = 6;
		this.overwriteBR2Button.Text = "Overwite";
		this.overwriteBR2Button.UseVisualStyleBackColor = true;
		this.overwriteBR2Button.Click += new System.EventHandler(OverwriteMeshesButtonClick);
		this.openButton.Location = new System.Drawing.Point(4, 5);
		this.openButton.Name = "openButton";
		this.openButton.Size = new System.Drawing.Size(57, 33);
		this.openButton.TabIndex = 2;
		this.openButton.Text = "Open";
		this.openButton.UseVisualStyleBackColor = true;
		this.openButton.Click += new System.EventHandler(OpenButtonClick);
		this.saveButton.Location = new System.Drawing.Point(248, 5);
		this.saveButton.Name = "saveButton";
		this.saveButton.Size = new System.Drawing.Size(66, 33);
		this.saveButton.TabIndex = 3;
		this.saveButton.Text = "Save";
		this.saveButton.UseVisualStyleBackColor = true;
		this.saveButton.Click += new System.EventHandler(SaveButtonClick);
		this.saveAsButton.Location = new System.Drawing.Point(320, 5);
		this.saveAsButton.Name = "saveAsButton";
		this.saveAsButton.Size = new System.Drawing.Size(70, 33);
		this.saveAsButton.TabIndex = 4;
		this.saveAsButton.Text = "Save As";
		this.saveAsButton.UseVisualStyleBackColor = true;
		this.saveAsButton.Click += new System.EventHandler(SaveAsButtonClick);
		this.saveAnimationButton.Location = new System.Drawing.Point(396, 5);
		this.saveAnimationButton.Name = "saveAnimationButton";
		this.saveAnimationButton.Size = new System.Drawing.Size(90, 33);
		this.saveAnimationButton.TabIndex = 5;
		this.saveAnimationButton.Text = "Save Anim.";
		this.saveAnimationButton.UseVisualStyleBackColor = true;
		this.saveAnimationButton.Click += new System.EventHandler(SaveAnimationClick);
		this.mainTabControl.Controls.Add(this.editModelTabPage);
		this.mainTabControl.Controls.Add(this.editMaterialsTabPage);
		this.mainTabControl.Controls.Add(this.otherActionsTabPage);
		this.mainTabControl.Controls.Add(this.furtherActionsTabPage);
		this.mainTabControl.Controls.Add(this.selectModelTabPage);
		this.mainTabControl.Dock = System.Windows.Forms.DockStyle.Fill;
		this.mainTabControl.Location = new System.Drawing.Point(0, 0);
		this.mainTabControl.Name = "mainTabControl";
		this.mainTabControl.SelectedIndex = 0;
		this.mainTabControl.Size = new System.Drawing.Size(492, 572);
		this.mainTabControl.TabIndex = 2;
		this.editModelTabPage.Controls.Add(this.editModelContainer);
		this.editModelTabPage.Location = new System.Drawing.Point(4, 25);
		this.editModelTabPage.Name = "editModelTabPage";
		this.editModelTabPage.Padding = new System.Windows.Forms.Padding(3);
		this.editModelTabPage.Size = new System.Drawing.Size(484, 543);
		this.editModelTabPage.TabIndex = 0;
		this.editModelTabPage.Text = "Edit Mesh Material Bindings";
		this.editModelTabPage.UseVisualStyleBackColor = true;
		this.editMaterialsTabPage.Controls.Add(this.editMaterialsContainer);
		this.editMaterialsTabPage.Location = new System.Drawing.Point(4, 25);
		this.editMaterialsTabPage.Name = "editMaterialsTabPage";
		this.editMaterialsTabPage.Padding = new System.Windows.Forms.Padding(3);
		this.editMaterialsTabPage.Size = new System.Drawing.Size(484, 543);
		this.editMaterialsTabPage.TabIndex = 1;
		this.editMaterialsTabPage.Text = "Edit Materials";
		this.editMaterialsTabPage.UseVisualStyleBackColor = true;
		this.editModelContainer.Dock = System.Windows.Forms.DockStyle.Left;
		this.editModelContainer.Location = new System.Drawing.Point(3, 3);
		this.editModelContainer.Name = "editModelContainer";
		this.editModelContainer.Orientation = System.Windows.Forms.Orientation.Horizontal;
		this.editModelContainer.Size = new System.Drawing.Size(480, 537);
		this.editModelContainer.SplitterDistance = 537;
		this.editModelContainer.TabIndex = 0;
		this.editModelContainer.Panel1.Controls.Add(this.meshList);
		this.editModelContainer.Panel1.Controls.Add(this.triangleGroupsList);
		this.editMaterialsContainer.Dock = System.Windows.Forms.DockStyle.Left;
		this.editMaterialsContainer.Location = new System.Drawing.Point(3, 3);
		this.editMaterialsContainer.Name = "editMaterialsContainer";
		this.editMaterialsContainer.Orientation = System.Windows.Forms.Orientation.Horizontal;
		this.editMaterialsContainer.Size = new System.Drawing.Size(480, 537);
		this.editMaterialsContainer.SplitterDistance = 537;
		this.editMaterialsContainer.TabIndex = 0;
		this.editMaterialsContainer.Panel1.Controls.Add(this.materialListPanelContainer);
		this.meshList.Columns.AddRange(new System.Windows.Forms.ColumnHeader[2] { this.MeshNameColumnHeader, this.TriangleGroupCountColumnHeader });
		this.meshList.Dock = System.Windows.Forms.DockStyle.Top;
		this.meshList.FullRowSelect = true;
		this.meshList.GridLines = true;
		this.meshList.Location = new System.Drawing.Point(0, 0);
		this.meshList.MultiSelect = false;
		this.meshList.Name = "meshList";
		this.meshList.Size = new System.Drawing.Size(480, 250);
		this.meshList.TabIndex = 2;
		this.meshList.UseCompatibleStateImageBehavior = false;
		this.meshList.View = System.Windows.Forms.View.Details;
		this.meshList.SelectedIndexChanged += new System.EventHandler(MeshListSelectedIndexChanged);
		this.TriangleGroupColumnHeader.Tag = "Triangle Group";
		this.TriangleGroupColumnHeader.Text = "Triangle Group";
		this.TriangleGroupColumnHeader.Width = 120;
		this.MaterialColumnHeader.Text = "Material";
		this.MaterialColumnHeader.Width = 356;
		this.triangleGroupsList.Columns.AddRange(new System.Windows.Forms.ColumnHeader[2] { this.TriangleGroupColumnHeader, this.MaterialColumnHeader });
		this.triangleGroupsList.Dock = System.Windows.Forms.DockStyle.Bottom;
		this.triangleGroupsList.FullRowSelect = true;
		this.triangleGroupsList.GridLines = true;
		this.triangleGroupsList.Location = new System.Drawing.Point(0, 260);
		this.triangleGroupsList.MultiSelect = false;
		this.triangleGroupsList.Name = "triangleGroupsList";
		this.triangleGroupsList.Size = new System.Drawing.Size(480, 250);
		this.triangleGroupsList.TabIndex = 3;
		this.triangleGroupsList.UseCompatibleStateImageBehavior = false;
		this.triangleGroupsList.View = System.Windows.Forms.View.Details;
		this.MeshNameColumnHeader.Tag = "Mesh Name";
		this.MeshNameColumnHeader.Text = "Mesh Name";
		this.MeshNameColumnHeader.Width = 326;
		this.TriangleGroupCountColumnHeader.Text = "Num Triangle Groups";
		this.TriangleGroupCountColumnHeader.Width = 150;
		this.materialListPanelContainer.Dock = System.Windows.Forms.DockStyle.Top;
		this.materialListPanelContainer.Location = new System.Drawing.Point(0, 0);
		this.materialListPanelContainer.Name = "materialListPanelContainer";
		this.materialListPanelContainer.Orientation = System.Windows.Forms.Orientation.Horizontal;
		this.materialListPanelContainer.Panel1.Controls.Add(this.materialList);
		this.materialListPanelContainer.Panel1.Controls.Add(this.materialButtonsPanel);
		this.materialListPanelContainer.SplitterDistance = 537;
		this.materialListPanelContainer.Size = new System.Drawing.Size(480, 537);
		this.materialList.Columns.AddRange(new System.Windows.Forms.ColumnHeader[2] { this.materialNameHeader, this.materialTypeHeader });
		this.materialList.Dock = System.Windows.Forms.DockStyle.Fill;
		this.materialList.FullRowSelect = true;
		this.materialList.GridLines = true;
		this.materialList.Location = new System.Drawing.Point(0, 0);
		this.materialList.Name = "materialList";
		this.materialList.Size = new System.Drawing.Size(480, 573);
		this.materialList.TabIndex = 6;
		this.materialList.UseCompatibleStateImageBehavior = false;
		this.materialList.View = System.Windows.Forms.View.Details;
		this.materialList.SelectedIndexChanged += new System.EventHandler(MaterialListSelectedIndexChanged);
		this.materialNameHeader.Text = "Material";
		this.materialNameHeader.Width = 180;
		this.materialTypeHeader.Text = "Type";
		this.materialTypeHeader.Width = 200;
		this.materialButtonsPanel.Controls.Add(this.addMaterialButton);
		this.materialButtonsPanel.Controls.Add(this.deleteMaterialButton);
		this.materialButtonsPanel.Controls.Add(this.clearMaterialsButton);
		this.materialButtonsPanel.Dock = System.Windows.Forms.DockStyle.Bottom;
		this.materialButtonsPanel.Location = new System.Drawing.Point(0, 131);
		this.materialButtonsPanel.Name = "materialButtonsPanel";
		this.materialButtonsPanel.Size = new System.Drawing.Size(480, 31);
		this.materialButtonsPanel.TabIndex = 7;
		this.addMaterialButton.Location = new System.Drawing.Point(12, 5);
		this.addMaterialButton.Name = "addMaterial";
		this.addMaterialButton.Size = new System.Drawing.Size(75, 23);
		this.addMaterialButton.TabIndex = 1;
		this.addMaterialButton.Text = "Add";
		this.addMaterialButton.UseVisualStyleBackColor = true;
		this.addMaterialButton.Click += new System.EventHandler(AddMaterialClick);
		this.deleteMaterialButton.Location = new System.Drawing.Point(95, 5);
		this.deleteMaterialButton.Name = "deleteMaterial";
		this.deleteMaterialButton.Size = new System.Drawing.Size(75, 23);
		this.deleteMaterialButton.TabIndex = 0;
		this.deleteMaterialButton.Text = "Delete";
		this.deleteMaterialButton.UseVisualStyleBackColor = true;
		this.deleteMaterialButton.Click += new System.EventHandler(DeleteMaterialClick);
		this.clearMaterialsButton.Location = new System.Drawing.Point(178, 5);
		this.clearMaterialsButton.Name = "deleteMaterial";
		this.clearMaterialsButton.Size = new System.Drawing.Size(75, 23);
		this.clearMaterialsButton.TabIndex = 0;
		this.clearMaterialsButton.Text = "Delete All";
		this.clearMaterialsButton.UseVisualStyleBackColor = true;
		this.clearMaterialsButton.Click += new System.EventHandler(ClearMaterialsClick);
		this.animationsTabControl.Controls.Add(this.grannyAnimsTabPage);
		this.animationsTabControl.Dock = System.Windows.Forms.DockStyle.Fill;
		this.animationsTabControl.Location = new System.Drawing.Point(0, 0);
		this.animationsTabControl.Name = "animationsTabControl";
		this.animationsTabControl.SelectedIndex = 0;
		this.animationsTabControl.Size = new System.Drawing.Size(480, 172);
		this.animationsTabControl.TabIndex = 1;
		this.grannyAnimsTabPage.Controls.Add(this.animList);
		this.grannyAnimsTabPage.Location = new System.Drawing.Point(4, 25);
		this.grannyAnimsTabPage.Name = "grannyAnimsTabPage";
		this.grannyAnimsTabPage.Padding = new System.Windows.Forms.Padding(3);
		this.grannyAnimsTabPage.Size = new System.Drawing.Size(472, 143);
		this.grannyAnimsTabPage.TabIndex = 0;
		this.grannyAnimsTabPage.Text = "Granny Anims";
		this.grannyAnimsTabPage.UseVisualStyleBackColor = true;
		this.animList.Columns.AddRange(new System.Windows.Forms.ColumnHeader[2] { this.anim, this.timeSlice });
		this.animList.Dock = System.Windows.Forms.DockStyle.Fill;
		this.animList.FullRowSelect = true;
		this.animList.GridLines = true;
		this.animList.Location = new System.Drawing.Point(3, 3);
		this.animList.Name = "animList";
		this.animList.Size = new System.Drawing.Size(466, 137);
		this.animList.TabIndex = 10;
		this.animList.UseCompatibleStateImageBehavior = false;
		this.animList.View = System.Windows.Forms.View.Details;
		this.anim.Text = "Animation";
		this.anim.Width = 100;
		this.timeSlice.Text = "Time Slice";
		this.timeSlice.Width = 98;
		this.otherActionsTabPage.Controls.Add(this.nodeLabel);
		this.otherActionsTabPage.Controls.Add(this.nodeTextBox);
		this.otherActionsTabPage.Controls.Add(this.openBR2Button);
		this.otherActionsTabPage.Controls.Add(this.fpsLevel);
		this.otherActionsTabPage.Controls.Add(this.fpsTextBox);
		this.otherActionsTabPage.Controls.Add(this.concatenateNA2Button);
		this.otherActionsTabPage.Controls.Add(this.angleLabel);
		this.otherActionsTabPage.Controls.Add(this.axisLabel);
		this.otherActionsTabPage.Controls.Add(this.axisComboBox);
		this.otherActionsTabPage.Controls.Add(this.geoClassNameComboBox);
		this.otherActionsTabPage.Controls.Add(this.vertexFormatComboBox);
		this.otherActionsTabPage.Controls.Add(this.endTimeTextBoxLabel);
		this.otherActionsTabPage.Controls.Add(this.startTimeTextBoxLabel);
		this.otherActionsTabPage.Controls.Add(this.geoClassNameLabel);
		this.otherActionsTabPage.Controls.Add(this.endTimeTextBox);
		this.otherActionsTabPage.Controls.Add(this.startTimeTextBox);
		this.otherActionsTabPage.Controls.Add(this.exportNA2Button);
		this.otherActionsTabPage.Controls.Add(this.rescaleBoneNameLabel);
		this.otherActionsTabPage.Controls.Add(this.rescaleNamedBoneButton);
		this.otherActionsTabPage.Controls.Add(this.bonesComboBox);
		this.otherActionsTabPage.Controls.Add(this.rescaleFactorLabel);
		this.otherActionsTabPage.Controls.Add(this.insertAdjustmentBoneButton);
		this.otherActionsTabPage.Controls.Add(this.exportBR2Button);
		this.otherActionsTabPage.Controls.Add(this.angleTextBox);
		this.otherActionsTabPage.Controls.Add(this.rescaleFactorTextBox);
		this.otherActionsTabPage.Controls.Add(this.xPositionLabel);
		this.otherActionsTabPage.Controls.Add(this.yPositionLabel);
		this.otherActionsTabPage.Controls.Add(this.zPositionLabel);
		this.otherActionsTabPage.Controls.Add(this.xPositionTextBox);
		this.otherActionsTabPage.Controls.Add(this.yPositionTextBox);
		this.otherActionsTabPage.Controls.Add(this.zPositionTextBox);
		this.otherActionsTabPage.Controls.Add(this.makeTemplateButton);
		this.otherActionsTabPage.Controls.Add(this.removeAnimationsButton);
		this.otherActionsTabPage.Controls.Add(this.removeNamedBoneButton);
		this.otherActionsTabPage.Controls.Add(this.resaveAllFBXAsAnimsButton);
		this.otherActionsTabPage.Controls.Add(this.vertexFormatLabel);
		this.otherActionsTabPage.Controls.Add(this.importExportFiletypesLabel);
		this.otherActionsTabPage.Controls.Add(this.importExportFormatBR2NB2RadioButton);
		this.otherActionsTabPage.Controls.Add(this.importExportFormatCN6RadioButton);
		this.otherActionsTabPage.Controls.Add(this.writeGeoFileButton);
		this.otherActionsTabPage.Controls.Add(this.loadStringDatabaseButton);
		this.otherActionsTabPage.Controls.Add(this.exportCurrentModelButton);
		this.otherActionsTabPage.Controls.Add(this.overwriteMeshesButton);
		this.otherActionsTabPage.Controls.Add(this.exportAllModelsButton);
		this.otherActionsTabPage.Location = new System.Drawing.Point(4, 25);
		this.otherActionsTabPage.Name = "otherActionsTabPage";
		this.otherActionsTabPage.Padding = new System.Windows.Forms.Padding(3);
		this.otherActionsTabPage.Size = new System.Drawing.Size(484, 543);
		this.otherActionsTabPage.TabIndex = 2;
		this.otherActionsTabPage.Text = "Additional Actions";
		this.otherActionsTabPage.UseVisualStyleBackColor = true;
		this.furtherActionsTabPage.Location = new System.Drawing.Point(4, 25);
		this.furtherActionsTabPage.Name = "texturesTabPage";
		this.furtherActionsTabPage.Size = new System.Drawing.Size(484, 543);
		this.furtherActionsTabPage.TabIndex = 3;
		this.furtherActionsTabPage.Text = "Further Actions";
		this.furtherActionsTabPage.UseVisualStyleBackColor = true;
		this.furtherActionsTabPage.Controls.Add(this.processTextureButton);
		this.furtherActionsTabPage.Controls.Add(this.processTexturesInDirButton);
		this.furtherActionsTabPage.Controls.Add(this.batchConversionButton);
		this.furtherActionsTabPage.Controls.Add(this.textureClassComboBox);
		this.furtherActionsTabPage.Controls.Add(this.textureClassLabel);
		this.furtherActionsTabPage.Controls.Add(this.assetClassNameComboBox);
		this.furtherActionsTabPage.Controls.Add(this.assetClassNameLabel);
		this.furtherActionsTabPage.Controls.Add(this.materialClassNameComboBox);
		this.furtherActionsTabPage.Controls.Add(this.materialClassNameLabel);
		this.furtherActionsTabPage.Controls.Add(this.dsgComboBox);
		this.furtherActionsTabPage.Controls.Add(this.dsgLabel);
		this.furtherActionsTabPage.Controls.Add(this.multiModelAssetCheckBox);
		this.furtherActionsTabPage.Controls.Add(this.multiModelAssetCheckBoxLabel);
		this.selectModelTabPage.Controls.Add(this.modelList);
		this.selectModelTabPage.Location = new System.Drawing.Point(4, 25);
		this.selectModelTabPage.Name = "selectModelTabPage";
		this.selectModelTabPage.Size = new System.Drawing.Size(484, 543);
		this.selectModelTabPage.TabIndex = 4;
		this.selectModelTabPage.Text = "Select Model";
		this.selectModelTabPage.UseVisualStyleBackColor = true;
		this.nodeLabel.AutoSize = true;
		this.nodeLabel.Location = new System.Drawing.Point(6, 328);
		this.nodeLabel.Name = "nodeLabel";
		this.nodeLabel.Size = new System.Drawing.Size(42, 17);
		this.nodeLabel.TabIndex = 47;
		this.nodeLabel.Text = "Node";
		this.nodeTextBox.Location = new System.Drawing.Point(52, 325);
		this.nodeTextBox.Name = "nodeTextBox";
		this.nodeTextBox.Size = new System.Drawing.Size(204, 22);
		this.nodeTextBox.TabIndex = 46;
		this.openBR2Button.Location = new System.Drawing.Point(6, 274);
		this.openBR2Button.Name = "openBR2Button";
		this.openBR2Button.Size = new System.Drawing.Size(250, 40);
		this.openBR2Button.TabIndex = 45;
		this.openBR2Button.Text = "Open FBX";
		this.openBR2Button.UseVisualStyleBackColor = true;
		this.openBR2Button.Click += new System.EventHandler(OpenFBXButtonClick);
		this.fpsLevel.AutoSize = true;
		this.fpsLevel.Location = new System.Drawing.Point(13, 197);
		this.fpsLevel.Name = "fpsLevel";
		this.fpsLevel.Size = new System.Drawing.Size(93, 17);
		this.fpsLevel.TabIndex = 44;
		this.fpsLevel.Text = "FPS Override";
		this.fpsTextBox.ForeColor = System.Drawing.SystemColors.ActiveCaptionText;
		this.fpsTextBox.Location = new System.Drawing.Point(117, 194);
		this.fpsTextBox.Name = "fpsTextBox";
		this.fpsTextBox.Size = new System.Drawing.Size(139, 22);
		this.fpsTextBox.TabIndex = 43;
		this.fpsTextBox.Text = "60";
		this.concatenateNA2Button.Location = new System.Drawing.Point(6, 228);
		this.concatenateNA2Button.Name = "concatenateNA2Button";
		this.concatenateNA2Button.Size = new System.Drawing.Size(250, 40);
		this.concatenateNA2Button.TabIndex = 42;
		this.concatenateNA2Button.Text = "Concatenate All NA2 Files in Directory";
		this.concatenateNA2Button.UseVisualStyleBackColor = true;
		this.concatenateNA2Button.Click += new System.EventHandler(ConcatenateNA2ButtonClick);
		this.angleLabel.AutoSize = true;
		this.angleLabel.Location = new System.Drawing.Point(260, 387);
		this.angleLabel.Name = "angleLabel";
		this.angleLabel.Size = new System.Drawing.Size(101, 17);
		this.angleLabel.TabIndex = 41;
		this.angleLabel.Text = "Rotation Angle";
		this.axisLabel.AutoSize = true;
		this.axisLabel.Location = new System.Drawing.Point(260, 357);
		this.axisLabel.Name = "axisLabel";
		this.axisLabel.Size = new System.Drawing.Size(33, 17);
		this.axisLabel.TabIndex = 41;
		this.axisLabel.Text = "Axis";
		this.axisComboBox.FormattingEnabled = true;
		this.axisComboBox.Items.AddRange(new object[3] { "X (Left-Right)", "Y (Forward-Back)", "Z (Up-Down)" });
		this.axisComboBox.Location = new System.Drawing.Point(316, 354);
		this.axisComboBox.Name = "axisComboBox";
		this.axisComboBox.Size = new System.Drawing.Size(159, 24);
		this.axisComboBox.TabIndex = 40;
		this.axisComboBox.Text = "Z (Up-Down)";
		this.geoClassNameLabel.AutoSize = true;
		this.geoClassNameLabel.Location = new System.Drawing.Point(260, 106);
		this.geoClassNameLabel.Name = "classNameTextBoxLabel";
		this.geoClassNameLabel.Size = new System.Drawing.Size(99, 17);
		this.geoClassNameLabel.TabIndex = 48;
		this.geoClassNameLabel.Text = "Geo Class";
		this.geoClassNameLabel.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
		this.geoClassNameComboBox.FormattingEnabled = true;
		this.geoClassNameComboBox.Items.AddRange(new object[9] { "DecalGeometry", "LandmarkModel", "LandmarkObstructionProfile", "Leader", "Leader_ShadowVolume", "UILensModel", "Unit", "VFXModel", "WonderMovieModel" });
		this.geoClassNameComboBox.Location = new System.Drawing.Point(316, 102);
		this.geoClassNameComboBox.Name = "classNameComboBox";
		this.geoClassNameComboBox.Size = new System.Drawing.Size(159, 24);
		this.geoClassNameComboBox.TabIndex = 47;
		this.geoClassNameComboBox.Text = "Unit";
		this.assetClassNameLabel.AutoSize = true;
		this.assetClassNameLabel.Location = new System.Drawing.Point(10, 120);
		this.assetClassNameLabel.Name = "assetClassNameLabel";
		this.assetClassNameLabel.Size = new System.Drawing.Size(99, 17);
		this.assetClassNameLabel.TabIndex = 48;
		this.assetClassNameLabel.Text = "Asset Class";
		this.assetClassNameLabel.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
		this.assetClassNameComboBox.FormattingEnabled = true;
		this.assetClassNameComboBox.Location = new System.Drawing.Point(90, 116);
		this.assetClassNameComboBox.Items.AddRange(new object[15]
		{
			"CityBlock", "Clutter", "Landmark", "Leader", "RouteDoodad", "StrategicView_DirectedAsset", "StrategicView_Route", "StrategicView_TerrainBlend", "StrategicView_TerrainBlendCorners", "TerrainElementAsset",
			"TileBase", "UILensAsset", "Unit", "VFX", "WonderMovie"
		});
		this.assetClassNameComboBox.Name = "assetClassNameComboBox";
		this.assetClassNameComboBox.Size = new System.Drawing.Size(159, 24);
		this.assetClassNameComboBox.TabIndex = 47;
		this.assetClassNameComboBox.Text = "Unit";
		this.materialClassNameLabel.AutoSize = true;
		this.materialClassNameLabel.Location = new System.Drawing.Point(10, 150);
		this.materialClassNameLabel.Name = "materialClassNameLabel";
		this.materialClassNameLabel.Size = new System.Drawing.Size(99, 17);
		this.materialClassNameLabel.TabIndex = 48;
		this.materialClassNameLabel.Text = "Material Class";
		this.materialClassNameLabel.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
		this.materialClassNameLabel.Hide();
		this.materialClassNameComboBox.FormattingEnabled = true;
		this.materialClassNameComboBox.Location = new System.Drawing.Point(90, 146);
		this.materialClassNameComboBox.Items.AddRange(new object[21]
		{
			"BurnMaterial", "DecalMaterial", "FOWLineDrawing", "Landmark", "Leader", "Leader_Cloth", "Leader_Glass", "Leader_Hair", "Leader_Matte", "Leader_Skin",
			"RiverWater", "SnowMaterial", "TerrainEditMaterial", "TerrainElement", "TerrainMaterial", "UILensMaterial", "Unit", "VFXModel", "VFXModel_FX", "Water",
			"WaveMaterial"
		});
		this.materialClassNameComboBox.Name = "materialClassNameComboBox";
		this.materialClassNameComboBox.Size = new System.Drawing.Size(159, 24);
		this.materialClassNameComboBox.TabIndex = 47;
		this.materialClassNameComboBox.Text = "Unit";
		this.materialClassNameComboBox.Hide();
		this.dsgLabel.AutoSize = true;
		this.dsgLabel.Location = new System.Drawing.Point(10, 180);
		this.dsgLabel.Name = "dsgLabel";
		this.dsgLabel.Size = new System.Drawing.Size(99, 17);
		this.dsgLabel.TabIndex = 48;
		this.dsgLabel.Text = "DSG";
		this.dsgLabel.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
		this.dsgComboBox.FormattingEnabled = true;
		this.dsgComboBox.Location = new System.Drawing.Point(90, 176);
		this.dsgComboBox.Items.AddRange(new object[22]
		{
			"Landmark_Activated", "Landmark_WaterMill", "potential_any_graph", "Standard_Biped", "Standard_Broadside", "Standard_CannonBlast", "Standard_Clutter", "Standard_Dog", "Standard_GunMuzzleFlash", "Standard_Landmark",
			"Standard_LandmarkNoRandomOffset", "Standard_Leader", "Standard_LeaderBackground", "Standard_Naval", "Standard_NonCombat", "Standard_NonCombatNaval", "Standard_SwordTrail", "Standard_TerrainElementAsset", "Standard_VFX", "Standard_VFX_RandomOffset",
			"Standard_WonderMovie", ""
		});
		this.dsgComboBox.Name = "dsgComboBox";
		this.dsgComboBox.Size = new System.Drawing.Size(159, 24);
		this.dsgComboBox.TabIndex = 47;
		this.dsgComboBox.Text = "potential_any_graph";
		this.multiModelAssetCheckBoxLabel.AutoSize = true;
		this.multiModelAssetCheckBoxLabel.Location = new System.Drawing.Point(50, 270);
		this.multiModelAssetCheckBoxLabel.Name = "multiModelAssetCheckBox";
		this.multiModelAssetCheckBoxLabel.Size = new System.Drawing.Size(99, 17);
		this.multiModelAssetCheckBoxLabel.TabIndex = 47;
		this.multiModelAssetCheckBoxLabel.Text = "Multi Model Asset Mode";
		this.multiModelAssetCheckBoxLabel.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
		this.multiModelAssetCheckBoxLabel.Hide();
		this.multiModelAssetCheckBox.Checked = false;
		this.multiModelAssetCheckBox.Location = new System.Drawing.Point(180, 265);
		this.multiModelAssetCheckBox.Hide();
		this.vertexFormatComboBox.FormattingEnabled = true;
		this.vertexFormatComboBox.Items.AddRange(new object[3] { "Bone Bindings, 1 UV", "No Bone Bindings, 2 UVs", "No Bone Bindings, 3 UVs" });
		this.vertexFormatComboBox.Location = new System.Drawing.Point(8, 382);
		this.vertexFormatComboBox.Name = "vertexFormatComboBox";
		this.vertexFormatComboBox.Size = new System.Drawing.Size(159, 24);
		this.vertexFormatComboBox.TabIndex = 47;
		this.vertexFormatComboBox.Text = "Bone Bindings, 1 UV";
		this.endTimeTextBoxLabel.AutoSize = true;
		this.endTimeTextBoxLabel.Location = new System.Drawing.Point(13, 170);
		this.endTimeTextBoxLabel.Name = "endTimeTextBoxLabel";
		this.endTimeTextBoxLabel.Size = new System.Drawing.Size(99, 17);
		this.endTimeTextBoxLabel.TabIndex = 39;
		this.endTimeTextBoxLabel.Text = "NA2 End Time";
		this.endTimeTextBoxLabel.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
		this.startTimeTextBoxLabel.AutoSize = true;
		this.startTimeTextBoxLabel.Location = new System.Drawing.Point(13, 143);
		this.startTimeTextBoxLabel.Name = "startTimeTextBoxLabel";
		this.startTimeTextBoxLabel.Size = new System.Drawing.Size(104, 17);
		this.startTimeTextBoxLabel.TabIndex = 38;
		this.startTimeTextBoxLabel.Text = "NA2 Start Time";
		this.startTimeTextBoxLabel.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
		this.endTimeTextBox.Location = new System.Drawing.Point(117, 167);
		this.endTimeTextBox.Name = "endTimeTextBox";
		this.endTimeTextBox.Size = new System.Drawing.Size(139, 22);
		this.endTimeTextBox.TabIndex = 37;
		this.startTimeTextBox.Location = new System.Drawing.Point(117, 140);
		this.startTimeTextBox.Name = "startTimeTextBox";
		this.startTimeTextBox.Size = new System.Drawing.Size(139, 22);
		this.startTimeTextBox.TabIndex = 37;
		this.exportNA2Button.Location = new System.Drawing.Point(6, 94);
		this.exportNA2Button.Name = "exportNA2Button";
		this.exportNA2Button.Size = new System.Drawing.Size(250, 40);
		this.exportNA2Button.TabIndex = 36;
		this.exportNA2Button.Text = "Export Animation to NA2";
		this.exportNA2Button.UseVisualStyleBackColor = true;
		this.exportNA2Button.Click += new System.EventHandler(ExportNA2ButtonClick);
		this.rescaleBoneNameLabel.AutoSize = true;
		this.rescaleBoneNameLabel.Location = new System.Drawing.Point(174, 505);
		this.rescaleBoneNameLabel.Name = "rescaleBoneNameLabel";
		this.rescaleBoneNameLabel.Size = new System.Drawing.Size(87, 17);
		this.rescaleBoneNameLabel.TabIndex = 35;
		this.rescaleBoneNameLabel.Text = "Parent Bone";
		this.rescaleNamedBoneButton.Location = new System.Drawing.Point(262, 458);
		this.rescaleNamedBoneButton.Name = "rescaleNamedBoneButton";
		this.rescaleNamedBoneButton.Size = new System.Drawing.Size(213, 38);
		this.rescaleNamedBoneButton.TabIndex = 34;
		this.rescaleNamedBoneButton.Text = "Add Scaled FX Bone and Save";
		this.rescaleNamedBoneButton.UseVisualStyleBackColor = true;
		this.rescaleNamedBoneButton.Click += new System.EventHandler(RescaleNamedBoneButtonClick);
		this.bonesComboBox.FormattingEnabled = true;
		this.bonesComboBox.Location = new System.Drawing.Point(262, 502);
		this.bonesComboBox.Name = "bonesComboBox";
		this.bonesComboBox.Size = new System.Drawing.Size(213, 24);
		this.bonesComboBox.TabIndex = 33;
		this.rescaleFactorLabel.AutoSize = true;
		this.rescaleFactorLabel.Location = new System.Drawing.Point(260, 328);
		this.rescaleFactorLabel.Name = "rescaleFactorLabel";
		this.rescaleFactorLabel.Size = new System.Drawing.Size(103, 17);
		this.rescaleFactorLabel.TabIndex = 32;
		this.rescaleFactorLabel.Text = "Rescale Factor";
		this.insertAdjustmentBoneButton.Location = new System.Drawing.Point(262, 228);
		this.insertAdjustmentBoneButton.Name = "insertAdjustmentBoneButton";
		this.insertAdjustmentBoneButton.Size = new System.Drawing.Size(213, 40);
		this.insertAdjustmentBoneButton.TabIndex = 31;
		this.insertAdjustmentBoneButton.Text = "Insert Adjustment Bone and Save";
		this.insertAdjustmentBoneButton.UseVisualStyleBackColor = true;
		this.insertAdjustmentBoneButton.Click += new System.EventHandler(InsertAdjustmentBoneClick);
		this.angleTextBox.Location = new System.Drawing.Point(366, 384);
		this.angleTextBox.Name = "angleTextBox";
		this.angleTextBox.Size = new System.Drawing.Size(109, 22);
		this.angleTextBox.TabIndex = 30;
		this.angleTextBox.Text = "90";
		this.rescaleFactorTextBox.Location = new System.Drawing.Point(366, 325);
		this.rescaleFactorTextBox.Name = "rescaleFactorTextBox";
		this.rescaleFactorTextBox.Size = new System.Drawing.Size(109, 22);
		this.rescaleFactorTextBox.TabIndex = 30;
		this.rescaleFactorTextBox.Text = "1";
		this.xPositionLabel.Location = new System.Drawing.Point(260, 287);
		this.xPositionLabel.Name = "xPositionLabel";
		this.xPositionLabel.Size = new System.Drawing.Size(28, 17);
		this.xPositionLabel.TabIndex = 32;
		this.xPositionLabel.Text = "X";
		this.yPositionLabel.Location = new System.Drawing.Point(335, 287);
		this.yPositionLabel.Name = "xPositionLabel";
		this.yPositionLabel.Size = new System.Drawing.Size(28, 17);
		this.yPositionLabel.TabIndex = 32;
		this.yPositionLabel.Text = "Y";
		this.zPositionLabel.Location = new System.Drawing.Point(410, 287);
		this.zPositionLabel.Name = "xPositionLabel";
		this.zPositionLabel.Size = new System.Drawing.Size(28, 17);
		this.zPositionLabel.TabIndex = 32;
		this.zPositionLabel.Text = "Z";
		this.xPositionTextBox.Location = new System.Drawing.Point(288, 284);
		this.xPositionTextBox.Name = "xPositionTextBox";
		this.xPositionTextBox.Size = new System.Drawing.Size(40, 22);
		this.xPositionTextBox.TabIndex = 40;
		this.xPositionTextBox.Text = "0";
		this.yPositionTextBox.Location = new System.Drawing.Point(363, 284);
		this.yPositionTextBox.Name = "yPositionTextBox";
		this.yPositionTextBox.Size = new System.Drawing.Size(40, 22);
		this.yPositionTextBox.TabIndex = 30;
		this.yPositionTextBox.Text = "0";
		this.zPositionTextBox.Location = new System.Drawing.Point(438, 284);
		this.zPositionTextBox.Name = "zPositionTextBox";
		this.zPositionTextBox.Size = new System.Drawing.Size(40, 22);
		this.zPositionTextBox.TabIndex = 30;
		this.zPositionTextBox.Text = "0";
		this.makeTemplateButton.Location = new System.Drawing.Point(262, 186);
		this.makeTemplateButton.Name = "makeTemplateButton";
		this.makeTemplateButton.Size = new System.Drawing.Size(213, 38);
		this.makeTemplateButton.TabIndex = 29;
		this.makeTemplateButton.Text = "Make Template";
		this.makeTemplateButton.UseVisualStyleBackColor = true;
		this.makeTemplateButton.Click += new System.EventHandler(MakeTemplateButtonClick);
		this.makeTemplateButton.Hide();
		this.removeAnimationsButton.Location = new System.Drawing.Point(262, 182);
		this.removeAnimationsButton.Name = "removeAnimationsButton";
		this.removeAnimationsButton.Size = new System.Drawing.Size(213, 40);
		this.removeAnimationsButton.TabIndex = 28;
		this.removeAnimationsButton.Text = "Remove Animations and Save";
		this.removeAnimationsButton.UseVisualStyleBackColor = true;
		this.removeAnimationsButton.Click += new System.EventHandler(RemoveAnimationsButtonClick);
		this.exportBR2Button.Location = new System.Drawing.Point(262, 228);
		this.exportBR2Button.Name = "exportBR2Button";
		this.exportBR2Button.Size = new System.Drawing.Size(213, 40);
		this.exportBR2Button.TabIndex = 46;
		this.exportBR2Button.Text = "Create Particle .ptl from .psb";
		this.exportBR2Button.UseVisualStyleBackColor = true;
		this.exportBR2Button.Click += new System.EventHandler(ConvertParticlePSBClick);
		this.exportBR2Button.Hide();
		this.removeNamedBoneButton.Location = new System.Drawing.Point(262, 412);
		this.removeNamedBoneButton.Name = "removeNamedBoneButton";
		this.removeNamedBoneButton.Size = new System.Drawing.Size(213, 38);
		this.removeNamedBoneButton.TabIndex = 34;
		this.removeNamedBoneButton.Text = "Remove Bone";
		this.removeNamedBoneButton.UseVisualStyleBackColor = true;
		this.removeNamedBoneButton.Click += new System.EventHandler(RemoveNamedBoneButtonClick);
		this.resaveAllFBXAsAnimsButton.Location = new System.Drawing.Point(262, 136);
		this.resaveAllFBXAsAnimsButton.Name = "resaveAllFBXAsAnimsButton";
		this.resaveAllFBXAsAnimsButton.Size = new System.Drawing.Size(213, 40);
		this.resaveAllFBXAsAnimsButton.TabIndex = 27;
		this.resaveAllFBXAsAnimsButton.Text = "Convert all .gr2 Files in Directory to .fgx/.anm";
		this.resaveAllFBXAsAnimsButton.UseVisualStyleBackColor = true;
		this.resaveAllFBXAsAnimsButton.Click += new System.EventHandler(ResaveAllGR2FilesInDirAsAnimsClick);
		this.vertexFormatLabel.AutoSize = true;
		this.vertexFormatLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 7.3125f, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, 0);
		this.vertexFormatLabel.Location = new System.Drawing.Point(6, 360);
		this.vertexFormatLabel.Name = "templateBR2OverwriteLabel";
		this.vertexFormatLabel.Size = new System.Drawing.Size(198, 16);
		this.vertexFormatLabel.TabIndex = 24;
		this.vertexFormatLabel.Text = "Mesh Vertex Format";
		this.importExportFiletypesLabel.AutoSize = true;
		this.importExportFiletypesLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 7.3125f, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, 0);
		this.importExportFiletypesLabel.Location = new System.Drawing.Point(6, 420);
		this.importExportFiletypesLabel.Name = "templateBR2OverwriteLabel2";
		this.importExportFiletypesLabel.Size = new System.Drawing.Size(198, 16);
		this.importExportFiletypesLabel.TabIndex = 24;
		this.importExportFiletypesLabel.Text = "Import/Export Filetype(s)";
		this.importExportFormatBR2NB2RadioButton.AutoSize = true;
		this.importExportFormatBR2NB2RadioButton.Location = new System.Drawing.Point(29, 472);
		this.importExportFormatBR2NB2RadioButton.Name = "useSceneTemplateRadioButton";
		this.importExportFormatBR2NB2RadioButton.Size = new System.Drawing.Size(161, 21);
		this.importExportFormatBR2NB2RadioButton.TabIndex = 23;
		this.importExportFormatBR2NB2RadioButton.TabStop = true;
		this.importExportFormatBR2NB2RadioButton.Text = "Nexus Buddy 2 (.br2/.nb2)";
		this.importExportFormatBR2NB2RadioButton.UseVisualStyleBackColor = true;
		this.importExportFormatCN6RadioButton.AutoSize = true;
		this.importExportFormatCN6RadioButton.Checked = true;
		this.importExportFormatCN6RadioButton.Location = new System.Drawing.Point(29, 446);
		this.importExportFormatCN6RadioButton.Name = "useLeaderTemplateRadioButton";
		this.importExportFormatCN6RadioButton.Size = new System.Drawing.Size(166, 21);
		this.importExportFormatCN6RadioButton.TabIndex = 22;
		this.importExportFormatCN6RadioButton.TabStop = true;
		this.importExportFormatCN6RadioButton.Text = "CivNexus6 (.cn6)";
		this.importExportFormatCN6RadioButton.UseVisualStyleBackColor = true;
		this.writeGeoFileButton.Location = new System.Drawing.Point(262, 50);
		this.writeGeoFileButton.Name = "writeGeoFileButton";
		this.writeGeoFileButton.Size = new System.Drawing.Size(213, 40);
		this.writeGeoFileButton.TabIndex = 18;
		this.writeGeoFileButton.Text = "Create Geometry/Animation (.geo/.anm) File";
		this.writeGeoFileButton.UseVisualStyleBackColor = true;
		this.writeGeoFileButton.Click += new System.EventHandler(WriteGeoFileButtonClick);
		this.exportCurrentModelButton.Location = new System.Drawing.Point(6, 50);
		this.exportCurrentModelButton.Name = "exportNB2CurrentModelButton";
		this.exportCurrentModelButton.Size = new System.Drawing.Size(250, 40);
		this.exportCurrentModelButton.TabIndex = 15;
		this.exportCurrentModelButton.Text = "Export Model (Current Model)";
		this.exportCurrentModelButton.UseVisualStyleBackColor = true;
		this.exportCurrentModelButton.Click += new System.EventHandler(ExportModel);
		this.overwriteMeshesButton.Location = new System.Drawing.Point(262, 228);
		this.overwriteMeshesButton.Name = "overwriteMeshesButton";
		this.overwriteMeshesButton.Size = new System.Drawing.Size(213, 40);
		this.overwriteMeshesButton.TabIndex = 14;
		this.overwriteMeshesButton.Text = "Overwrite Meshes";
		this.overwriteMeshesButton.UseVisualStyleBackColor = true;
		this.overwriteMeshesButton.Click += new System.EventHandler(OverwriteMeshesButtonClick);
		this.overwriteMeshesButton.Hide();
		this.exportAllModelsButton.Location = new System.Drawing.Point(6, 6);
		this.exportAllModelsButton.Name = "exportNB2Button";
		this.exportAllModelsButton.Size = new System.Drawing.Size(250, 40);
		this.exportAllModelsButton.TabIndex = 11;
		this.exportAllModelsButton.Text = "Export Models (All Models)";
		this.exportAllModelsButton.UseVisualStyleBackColor = true;
		this.exportAllModelsButton.Click += new System.EventHandler(ExportAllModels);
		this.processTextureButton.Location = new System.Drawing.Point(6, 50);
		this.processTextureButton.Name = "processTextureButton";
		this.processTextureButton.Size = new System.Drawing.Size(250, 40);
		this.processTextureButton.TabIndex = 11;
		this.processTextureButton.Text = "Process Texture into .dds/.tex";
		this.processTextureButton.UseVisualStyleBackColor = true;
		this.processTextureButton.Click += new System.EventHandler(ProcessTextureClick);
		this.processTexturesInDirButton.Location = new System.Drawing.Point(260, 50);
		this.processTexturesInDirButton.Name = "processTexturesInDirButton";
		this.processTexturesInDirButton.Size = new System.Drawing.Size(210, 40);
		this.processTexturesInDirButton.TabIndex = 11;
		this.processTexturesInDirButton.Text = "Process All Textures in Directory";
		this.processTexturesInDirButton.UseVisualStyleBackColor = true;
		this.processTexturesInDirButton.Click += new System.EventHandler(ProcessTexturesInDirectoryClick);
		this.batchConversionButton.Location = new System.Drawing.Point(6, 210);
		this.batchConversionButton.Name = "batchConversionButton";
		this.batchConversionButton.Size = new System.Drawing.Size(250, 40);
		this.batchConversionButton.TabIndex = 11;
		this.batchConversionButton.Text = "Batch Conversion Civ 5 -> Civ 6";
		this.batchConversionButton.UseVisualStyleBackColor = true;
		this.batchConversionButton.Click += new System.EventHandler(BatchConversionAction);
		this.batchConversionButton.Hide();
		this.textureClassComboBox.FormattingEnabled = true;
		this.textureClassComboBox.Location = new System.Drawing.Point(80, 12);
		this.textureClassComboBox.Name = "textureClassComboBox";
		this.textureClassComboBox.Size = new System.Drawing.Size(213, 24);
		this.textureClassComboBox.TabIndex = 33;
		System.Windows.Forms.ComboBox.ObjectCollection items = this.textureClassComboBox.Items;
		object[] items2 = NexusBuddy.GrannyInfos.TextureClass.GetAllTextureClasses().Keys.ToArray();
		items.AddRange(items2);
		this.textureClassComboBox.Text = "Generic_BaseColor";
		this.textureClassLabel.AutoSize = true;
		this.textureClassLabel.Location = new System.Drawing.Point(6, 15);
		this.textureClassLabel.Name = "textureClassLabel";
		this.textureClassLabel.Size = new System.Drawing.Size(198, 16);
		this.textureClassLabel.TabIndex = 24;
		this.textureClassLabel.Text = "Texture Class";
		this.modelList.CheckBoxes = true;
		this.modelList.Columns.AddRange(new System.Windows.Forms.ColumnHeader[1] { this.modelName });
		this.modelList.Dock = System.Windows.Forms.DockStyle.Fill;
		this.modelList.FullRowSelect = true;
		this.modelList.GridLines = true;
		this.modelList.HeaderStyle = System.Windows.Forms.ColumnHeaderStyle.Nonclickable;
		this.modelList.Location = new System.Drawing.Point(0, 0);
		this.modelList.MultiSelect = false;
		this.modelList.Name = "modelList";
		this.modelList.Size = new System.Drawing.Size(484, 543);
		this.modelList.TabIndex = 0;
		this.modelList.UseCompatibleStateImageBehavior = false;
		this.modelList.View = System.Windows.Forms.View.Details;
		this.modelList.ItemCheck += new System.Windows.Forms.ItemCheckEventHandler(ModelListCheckChanged);
		this.modelName.Text = "Model Name";
		this.modelName.Width = 300;
		this.panel1.Controls.Add(this.headerFilenameLabel);
		this.panel1.Controls.Add(this.viewButton);
		this.panel1.Dock = System.Windows.Forms.DockStyle.Top;
		this.panel1.Location = new System.Drawing.Point(0, 0);
		this.panel1.Name = "panel1";
		this.panel1.Size = new System.Drawing.Size(512, 42);
		this.panel1.TabIndex = 8;
		this.headerFilenameLabel.AutoSize = true;
		this.headerFilenameLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 10f, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, 0);
		this.headerFilenameLabel.Location = new System.Drawing.Point(3, 12);
		this.headerFilenameLabel.Name = "headerFilenameLabel";
		this.headerFilenameLabel.Size = new System.Drawing.Size(110, 20);
		this.headerFilenameLabel.TabIndex = 3;
		this.headerFilenameLabel.Text = "No file open";
		this.viewButton.Location = new System.Drawing.Point(412, 3);
		this.viewButton.Name = "viewButton";
		this.viewButton.Size = new System.Drawing.Size(97, 35);
		this.viewButton.TabIndex = 6;
		this.viewButton.Text = "View";
		this.viewButtonToolTip.SetToolTip(this.viewButton, "View .fbx in Granny Viewer");
		this.viewButton.UseVisualStyleBackColor = true;
		this.viewButton.Click += new System.EventHandler(ViewButtonClick);
		this.fileInfoGroupBox.Controls.Add(this.fileInfoTextBox);
		this.fileInfoGroupBox.Dock = System.Windows.Forms.DockStyle.Bottom;
		this.fileInfoGroupBox.Location = new System.Drawing.Point(0, 46);
		this.fileInfoGroupBox.Name = "fileInfoGroupBox";
		this.fileInfoGroupBox.Size = new System.Drawing.Size(512, 159);
		this.fileInfoGroupBox.TabIndex = 2;
		this.fileInfoGroupBox.TabStop = false;
		this.fileInfoGroupBox.Text = "Current File Info";
		this.fileInfoTextBox.Dock = System.Windows.Forms.DockStyle.Fill;
		this.fileInfoTextBox.Enabled = false;
		this.fileInfoTextBox.Location = new System.Drawing.Point(3, 18);
		this.fileInfoTextBox.Name = "fileInfoTextBox";
		this.fileInfoTextBox.Size = new System.Drawing.Size(506, 138);
		this.fileInfoTextBox.TabIndex = 0;
		this.fileInfoTextBox.Text = "";
		this.properties.Dock = System.Windows.Forms.DockStyle.Bottom;
		this.properties.Location = new System.Drawing.Point(0, 205);
		this.properties.Name = "properties";
		this.properties.Size = new System.Drawing.Size(512, 413);
		this.properties.TabIndex = 0;
		this.properties.PropertyValueChanged += new System.Windows.Forms.PropertyValueChangedEventHandler(PropertiesPropertyValueChanged);
		this.animation.Tag = "";
		this.animation.Text = "Animation";
		this.animation.Width = 149;
		this.duration.Text = "Duration";
		this.duration.Width = 94;
		this.materialTypeColumnHeader.Text = "Material Type";
		this.materialTypeColumnHeader.Width = 138;
		this.materialNameColumnHeader.Tag = "";
		this.materialNameColumnHeader.Text = "Material Name";
		this.materialNameColumnHeader.Width = 149;
		this.br2ImportButton.Location = new System.Drawing.Point(0, 0);
		this.br2ImportButton.Name = "br2ImportButton";
		this.br2ImportButton.Size = new System.Drawing.Size(75, 23);
		this.br2ImportButton.TabIndex = 0;
		this.loadStringDatabaseButton.Location = new System.Drawing.Point(262, 6);
		this.loadStringDatabaseButton.Name = "loadStringDatabaseButton";
		this.loadStringDatabaseButton.Size = new System.Drawing.Size(213, 40);
		this.loadStringDatabaseButton.TabIndex = 17;
		this.loadStringDatabaseButton.Text = "Create GeometrySet .xml for .ast file";
		this.loadStringDatabaseButton.UseVisualStyleBackColor = true;
		this.loadStringDatabaseButton.Click += new System.EventHandler(WriteGeometrySetDataClick);
		base.ClientSize = new System.Drawing.Size(1008, 618);
		base.Controls.Add(this.masterSplitContainer);
		base.Icon = (System.Drawing.Icon)resources.GetObject("$this.Icon");
		base.Name = "CivNexusSixApplicationForm";
		this.Text = this.GetApplicationNameWithVersionNumber() + " - Graphics Tool for Civilization VI";
		this.masterSplitContainer.Panel1.ResumeLayout(false);
		this.masterSplitContainer.Panel2.ResumeLayout(false);
		((System.ComponentModel.ISupportInitialize)this.masterSplitContainer).EndInit();
		this.masterSplitContainer.ResumeLayout(false);
		this.leftHandSplitContainer.Panel1.ResumeLayout(false);
		this.leftHandSplitContainer.Panel2.ResumeLayout(false);
		((System.ComponentModel.ISupportInitialize)this.leftHandSplitContainer).EndInit();
		this.leftHandSplitContainer.ResumeLayout(false);
		this.mainButtonPanel.ResumeLayout(false);
		this.mainTabControl.ResumeLayout(false);
		this.editModelTabPage.ResumeLayout(false);
		this.editModelContainer.Panel1.ResumeLayout(false);
		this.editModelContainer.Panel2.ResumeLayout(false);
		((System.ComponentModel.ISupportInitialize)this.editModelContainer).EndInit();
		this.editModelContainer.ResumeLayout(false);
		this.materialListPanelContainer.Panel1.ResumeLayout(false);
		((System.ComponentModel.ISupportInitialize)this.materialListPanelContainer).EndInit();
		this.materialListPanelContainer.ResumeLayout(false);
		this.materialButtonsPanel.ResumeLayout(false);
		this.animationsTabControl.ResumeLayout(false);
		this.grannyAnimsTabPage.ResumeLayout(false);
		this.otherActionsTabPage.ResumeLayout(false);
		this.otherActionsTabPage.PerformLayout();
		this.selectModelTabPage.ResumeLayout(false);
		this.furtherActionsTabPage.ResumeLayout(false);
		this.panel1.ResumeLayout(false);
		this.panel1.PerformLayout();
		this.fileInfoGroupBox.ResumeLayout(false);
		base.ResumeLayout(false);
	}
}
You are not using the latest version of the tool, please update.
Latest version is '11.1.0.9782' (yours is '9.1.0.7988')
