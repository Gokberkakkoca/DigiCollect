from kivy.utils import platform
from jnius import autoclass, cast
from android.runnable import run_on_ui_thread

# Android sınıfları
if platform == 'android':
    WindowManager = autoclass('android.view.WindowManager')
    LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
    Gravity = autoclass('android.view.Gravity')
    View = autoclass('android.view.View')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    ImageButton = autoclass('android.widget.ImageButton')
    PixelFormat = autoclass('android.graphics.PixelFormat')
    Context = autoclass('android.content.Context')

class FloatingButtonService:
    def __init__(self):
        self.button = None
        self.window_manager = None
        self.layout_params = None
        self.is_showing = False
        
        if platform == 'android':
            self.setup_android_service()
    
    def setup_android_service(self):
        """Android servisini hazırla"""
        activity = PythonActivity.mActivity
        self.window_manager = activity.getSystemService(Context.WINDOW_SERVICE)
        
        # Layout parametrelerini ayarla
        self.layout_params = LayoutParams()
        self.layout_params.type = LayoutParams.TYPE_APPLICATION_OVERLAY
        self.layout_params.flags = (LayoutParams.FLAG_NOT_FOCUSABLE | 
                                  LayoutParams.FLAG_NOT_TOUCH_MODAL |
                                  LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH)
        self.layout_params.format = PixelFormat.TRANSLUCENT
        self.layout_params.width = LayoutParams.WRAP_CONTENT
        self.layout_params.height = LayoutParams.WRAP_CONTENT
        self.layout_params.gravity = Gravity.RIGHT | Gravity.CENTER_VERTICAL
        
        # Floating butonu oluştur
        self.create_floating_button()
    
    @run_on_ui_thread
    def create_floating_button(self):
        """Floating butonu oluştur"""
        activity = PythonActivity.mActivity
        self.button = ImageButton(activity)
        
        # Buton resmini ayarla
        resources = activity.getResources()
        package_name = activity.getPackageName()
        drawable_id = resources.getIdentifier('ic_floating_button', 'drawable', package_name)
        self.button.setImageResource(drawable_id)
        
        # Tıklama olayını ekle
        self.button.setOnClickListener(ButtonClickListener())
    
    def show(self):
        """Floating butonu göster"""
        if not self.is_showing and platform == 'android':
            try:
                self.window_manager.addView(self.button, self.layout_params)
                self.is_showing = True
            except Exception as e:
                print(f"Floating buton gösterilemedi: {e}")
    
    def hide(self):
        """Floating butonu gizle"""
        if self.is_showing and platform == 'android':
            try:
                self.window_manager.removeView(self.button)
                self.is_showing = False
            except Exception as e:
                print(f"Floating buton gizlenemedi: {e}")
    
    def update_position(self, x, y):
        """Floating buton pozisyonunu güncelle"""
        if self.is_showing and platform == 'android':
            self.layout_params.x = x
            self.layout_params.y = y
            self.window_manager.updateViewLayout(self.button, self.layout_params)

class ButtonClickListener:
    """Buton tıklama olayı dinleyicisi"""
    def __init__(self):
        self.context = cast('android.content.Context', PythonActivity.mActivity)
    
    def onClick(self, view):
        """Butona tıklandığında"""
        # DigiCollect uygulamasını aç
        package_name = self.context.getPackageName()
        intent = self.context.getPackageManager().getLaunchIntentForPackage(package_name)
        intent.addFlags(0x10000000)  # FLAG_ACTIVITY_NEW_TASK
        self.context.startActivity(intent)
        
        # İçerik kesme ekranını aç
        # TODO: İçerik kesme ekranını açma kodu eklenecek
