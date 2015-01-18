package core;

import static org.lwjgl.opengl.GL11.*;
import static org.lwjgl.opengl.GL20.*;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;

import org.lwjgl.opengl.Display;

public class Shaders {

	private static Map<String, Shader> shaders = new HashMap<String, Shader>();
	
	static {
		shaders.put("NONE", new Shader("", "", "NONE"));
	}
	
	public static void registerShader(String vert, String frag, String name) {
		shaders.put(name, new Shader(vert, frag, name));
	}
	
	public static int getShaderByName(String name) {
		return shaders.get(name).getShaderID();
	}
	
	public static void useShader(String name) {
		glUseProgram(shaders.get(name).getShaderID());
	}
	
	public static void cleanup() {
		for (Entry<String, Shader> e : shaders.entrySet()) {
			glDeleteShader(e.getValue().getShaderID());
			glDeleteShader(e.getValue().getFragmentShader());
			glDeleteShader(e.getValue().getVertexShader());
		}
	}
	
	private static class Shader {
		private int shaderProgram;
		private int fragmentShader;
		private int vertexShader;
		
		int getShaderID() {
			return shaderProgram;
		}
		
		int getFragmentShader() {
			return vertexShader;
		}
		
		int getVertexShader() {
			return fragmentShader;
		}
		
		private Shader(String vert, String frag, String name) {
			if (name == "NONE") {
				return;
			}
			File vertShader = new File(vert);
			File fragShader = new File(frag);

			if (!(vertShader.exists() && fragShader.exists())) {
				System.out.println("Shaders files don't exist");
				return;
			}

			vertexShader = glCreateShader(GL_VERTEX_SHADER);
			fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);

			StringBuilder vertexShaderSource = new StringBuilder();
			StringBuilder fragmentShaderSource = new StringBuilder();

			try {
				BufferedReader reader = new BufferedReader(new FileReader(vertShader));
				String line;
				while ((line = reader.readLine()) != null) {
					vertexShaderSource.append(line).append("\n");
				}
				reader.close();
			} catch (IOException e) {
				System.err.println("Vertex shader not loaded");
				Display.destroy();
				System.exit(1);
			}

			try {
				BufferedReader reader = new BufferedReader(new FileReader(fragShader));
				String line;
				while ((line = reader.readLine()) != null) {
					fragmentShaderSource.append(line).append("\n");
				}
				reader.close();
			} catch (IOException e) {
				System.err.println("Fragment shader not loaded");
				Display.destroy();
				System.exit(1);
			}

			glShaderSource(vertexShader, vertexShaderSource);
			glShaderSource(fragmentShader, fragmentShaderSource);

			glCompileShader(vertexShader);
			if (glGetShader(vertexShader, GL_COMPILE_STATUS) == GL_FALSE) {
				System.err.println("Vertex shader not compiled");
				System.err.println(glGetString(glGetError()));
			}

			glCompileShader(fragmentShader);
			if (glGetShader(fragmentShader, GL_COMPILE_STATUS) == GL_FALSE) {
				System.err.println("Fragment shader not compiled");
				System.err.println(glGetString(glGetError()));
			}

			shaderProgram = glCreateProgram();

			glAttachShader(shaderProgram, vertexShader);
			glAttachShader(shaderProgram, fragmentShader);

			glLinkProgram(shaderProgram);
			glValidateProgram(shaderProgram);

			System.out.println("Shader " + name + " loaded successfully: " + (glGetProgram(shaderProgram, GL_LINK_STATUS) == GL_TRUE));
		}
	}
}