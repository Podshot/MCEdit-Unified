package level;

import static org.lwjgl.opengl.GL11.*;

import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.Display;

import core.Camera;
import core.Settings;
import core.Shaders;
import de.matthiasmann.twl.utils.PNGDecoder;
import entities.Entity;

public final class World {

	List<Entity> entities = new ArrayList<>();
	List<Entity> entitiesToAdd = new ArrayList<>();
	List<Entity> entitiesToRemove = new ArrayList<>();
	float[][] data = new float[256][256];
	private int heightmapDisplayList;
	private int lookupTexture;

	public World() throws IOException {
		BufferedImage map = ImageIO.read(new File("res/map.png"));
		for (int z = 0; z < data.length; z++) {
			for (int x = 0; x < data[0].length; x++) {
				data[z][x] = new Color(map.getRGB(z, x)).getRed();
			}
		}

		FileInputStream heightmapLookupInputStream = new FileInputStream("res/heightmap_lookup.png");
		PNGDecoder decoder = new PNGDecoder(heightmapLookupInputStream);
		ByteBuffer buffer = BufferUtils.createByteBuffer(4 * decoder.getWidth() * decoder.getHeight());
		decoder.decode(buffer, decoder.getWidth() * 4, PNGDecoder.Format.RGBA);
		buffer.flip();
		heightmapLookupInputStream.close();
		lookupTexture = glGenTextures();
		glBindTexture(GL_TEXTURE_2D, lookupTexture);
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, decoder.getWidth(), decoder.getHeight(), 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		
		registerMap();
	}
	
	public void render() {
		Shaders.useShader("terrain");
		glCallList(heightmapDisplayList);
		Shaders.useShader("NONE");
		
		if (Settings.CROSSVIEW) {
			Camera.make2D();
			glPushMatrix();
			glLoadIdentity();
			glTranslatef(Display.getWidth()/2f, Display.getHeight() - 100, 0);
			glBegin(GL_QUADS);
			glVertex2f(0, 0);
			glVertex2f(50, 0);
			glVertex2f(50, 50);
			glVertex2f(0, 50);
			glEnd();
			glPopMatrix();
			Camera.make3D();
		}
	}

	public void update() {
		for (Entity e : entitiesToAdd) {
			entities.add(e);
		}
		entitiesToAdd.clear();

		for (Entity e : getEntities()) {
			if (e.toBeRemoved()) {
				entitiesToRemove.add(e);
			} else {
				e.update();
			}
		}
		for (Entity e : entitiesToRemove) {
			getEntities().remove(e);
		}

		entitiesToRemove.clear();
	}
	
	boolean isFlat(int x, int z) {
		float height = data[z][x];
		boolean x1 = data[z][x-1] == height;
		boolean x2 = data[z][x+1] == height;
		boolean y1 = data[z-1][x] == height;
		boolean y2 = data[z+1][x] == height;
		
		return x1 && x2 && y1 && y2;
	}
	
	public boolean isSloped(int x, int z) {
		return !isFlat(x, z);
	}

	public void registerMap() {
		heightmapDisplayList = glGenLists(1);
		glNewList(heightmapDisplayList, GL_COMPILE);
		glScalef(-1f, 1f, -1f);
		for (int z = 1; z < data.length -2; z++) {
			glBegin(GL_TRIANGLE_STRIP);
			for (int x = 1; x < data[z].length - 2; x++) {
				//TODO improve visibility of isSloped(x, z+1)s
				glColor3f(isSloped(x, z+1) ? 0.95f : 1f, isSloped(x, z+1) ? 0.95f : 1f, isSloped(x, z+1) ? 0.95f : 1f);
				glVertex3f(x, -data[z+1][x], z+1);
				glColor3f(isSloped(x, z) ? 0.95f : 1f, isSloped(x, z) ? 0.95f : 1f, isSloped(x, z) ? 0.95f : 1f);
				glVertex3f(x, -data[z][x], z);
			}
			glEnd();
		}
		glEndList();
	}

	public float getHeight(float x, float z) throws ArrayIndexOutOfBoundsException {
		return data[(int) z][(int) x];
	}

	public List<Entity> getEntities() {
		return entities;
	}

	public void addEntity(Entity e) {
		entitiesToAdd.add(e);
	}

	public Entity getPlayer() {
		return getEntities().get(0);
	}

}
