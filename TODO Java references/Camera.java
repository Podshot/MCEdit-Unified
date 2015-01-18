package core;
import static org.lwjgl.opengl.GL11.*;
import static org.lwjgl.util.glu.GLU.*;

import java.awt.GraphicsDevice;
import java.awt.GraphicsEnvironment;
import java.nio.FloatBuffer;

import level.Location;

import org.lwjgl.BufferUtils;
import org.lwjgl.LWJGLException;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;

public class Camera {

    static Location loc;

    private static int width;
    private static int height;
    
    private static int winWidth;
    private static int winHeight;

    private static float fov;
    private static float aspect;
    private static float near;// 0 for bugs :D

    private static boolean setup = false;

    private static GraphicsDevice gd = GraphicsEnvironment.getLocalGraphicsEnvironment().getDefaultScreenDevice();
    private static int screenWidth = gd.getDisplayMode().getWidth();
    private static int screenHeight = gd.getDisplayMode().getHeight();

    public static void setup(float fov, float near) {
        if (setup)
            return;
        loc = new Location(0, 0, 0, 0, 0, 0, null);
        Camera.fov = fov;
        Camera.near = near;

        updateView();
        init();
        make3D();
        setup = true;
    }

    public static void make3D() {
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        gluPerspective(fov, aspect, near, Settings.RENDER_DISTANCE * 16 / 2);

        glEnable(GL_DEPTH_TEST);
        glEnable(GL_CULL_FACE);
        glCullFace(GL_BACK);

        glMatrixMode(GL_MODELVIEW);
    }

    public static void make2D() {
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(0.0f, width, height, 0.0f, 0.0f, 1.0f);

        glDisable(GL_DEPTH_TEST);
        glDisable(GL_CULL_FACE);

        glMatrixMode(GL_MODELVIEW);
    }

    public static void enableTextures() {
        glEnable(GL_TEXTURE_2D);
    }

    public static void disableTextures() {
        glDisable(GL_TEXTURE_2D);
    }

    public static void resize(boolean fs) throws LWJGLException {
        if (!Display.isFullscreen()) {
            winWidth = Display.getWidth();
            winHeight = Display.getHeight();
        }

        int awidth = (fs ? screenWidth : winWidth);
        int aheight = (fs ? screenHeight : winHeight);

        DisplayMode displayMode = null;
        DisplayMode[] modes = Display.getAvailableDisplayModes();

        if (fs != Settings.FULLSCREEN) {
            Settings.FULLSCREEN = fs;
            Display.setFullscreen(fs);

            for (int i = 0; i < modes.length; i++) {
                if (modes[i].getWidth() == awidth && modes[i].getHeight() == aheight && modes[i].isFullscreenCapable()) {
                    displayMode = modes[i];
                }
            }

            Display.setDisplayMode(displayMode != null ? displayMode : new DisplayMode(awidth, aheight));
        }

        glViewport(0, 0, awidth, aheight);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(0, awidth, aheight, 0, -1, 1);

        Camera.updateView();
        Display.setResizable(true);
    }
    
    public static void setWireframeEnabled(boolean wf) {
    	if (wf) {
    		glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
    	} else {
    		glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
    	}
    }

    private static void init() {
    	glEnable(GL_BLEND);
    	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    	glEnable(GL_LINE_SMOOTH);
    	glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);
    	
    	glEnableClientState(GL_VERTEX_ARRAY);
		glEnableClientState(GL_TEXTURE_COORD_ARRAY);
    	
        glLineWidth(1f);

        glEnable(GL_FOG);
        {
            FloatBuffer fogColor = BufferUtils.createFloatBuffer(4);
            fogColor.put(0.6f).put(0.6f).put(0.8f).put(0.8f).flip();

            glFogi(GL_FOG_MODE, GL_LINEAR);
            glFog(GL_FOG_COLOR, fogColor);
            glHint(GL_FOG_HINT, GL_DONT_CARE);
            glFogf(GL_FOG_START, Settings.RENDER_DISTANCE * 15 / 2);
            glFogf(GL_FOG_END, Settings.RENDER_DISTANCE * 16 / 2);
        }
        glClearColor(0.58f, 0.75f, 0.95f, 1f);
    }

    public static void updateView() {
        Camera.width = Display.getWidth();
        Camera.height = Display.getHeight();
        Camera.aspect = (float) Camera.width / (float) Camera.height;
        gluPerspective(fov, aspect, near, Settings.RENDER_DISTANCE * 16 / 2);
    }

    public static void useView() {
        glRotatef(loc.getRX(), 1, 0, 0);
        glRotatef(loc.getRY(), 0, 1, 0);
        glRotatef(loc.getRZ(), 0, 0, 1);
        glTranslatef(loc.getX(), loc.getY(), loc.getZ());
    }

    public static Location getLocation() {
        return loc;
    }

    public static void setLocation(Location loc) {
        Camera.loc = loc;
        Camera.useView();
    }

    public static void move(float amt, float dir) {
        loc.setZ((float) (loc.getZ() + amt * Math.sin(Math.toRadians(loc.getRY() + 90 * dir))));
        loc.setX((float) (loc.getX() + amt * Math.cos(Math.toRadians(loc.getRY() + 90 * dir))));
    }

    public static void rotateX(float x) {
        loc.setRX(loc.getRX() + x);

        if (loc.getRX() > 270) {
            loc.setRX(270);
        } else if (loc.getRX() < 90) {
            loc.setRX(90);
        }
    }

    public static void rotateY(float y) {
        loc.setRY((loc.getRY() + y) % 360);
    }

    public static void rotateZ(float z) {
        loc.setRZ((loc.getRZ() + z) % 360);
    }

    public static void setFov(float fov) {
        Camera.fov = fov;
        updateView();
    }
    
    public static float getFov() {
        return fov;
    }
}
