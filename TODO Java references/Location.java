package level;
public class Location {

    private float x;
    private float y;
    private float z;
    private float rx;
    private float ry;
    private float rz;
    private World world;

    public Location(float x, float y, float z, float rx, float ry, float rz, World world) {
        this.x = x;
        this.y = y;
        this.z = z;
        this.rx = rx;
        this.ry = ry;
        this.rz = rz;
        this.world = world;
    }

    public float getX() {
        return x;
    }

    public float getY() {
        return y;
    }

    public float getZ() {
        return z;
    }

    public float getRX() {
        return rx;
    }

    public void setRX(float rx) {
        this.rx = rx;
    }

    public float getRY() {
        return ry;
    }

    public void setRY(float ry) {
        this.ry = ry;
    }

    public float getRZ() {
        return rz;
    }

    public void setRZ(float rz) {
        this.rz = rz;
    }

    public void setX(float x) {
        this.x = x;
    }

    public void setY(float y) {
        this.y = y;
    }

    public void setZ(float z) {
        this.z = z;
    }

    public Location add(float x, float y, float z) {
        return new Location(this.x + x, this.y + y, this.z + z, this.rx, this.ry, this.rz, world);
    }

    public void addTo(float x, float y, float z) {
        this.x += x;
        this.y += y;
        this.z += z;
    }

    public World getWorld() {
        return world;
    }

    @Override
    public int hashCode() {
        return 0;
    }

    @Override
    public boolean equals(Object obj) {
        if (obj == null) {
            return false;
        }
        if (getClass() != obj.getClass()) {
            return false;
        }
        final Location other = (Location) obj;
        if (Float.floatToIntBits(this.x) != Float.floatToIntBits(other.x)) {
            return false;
        }
        if (Float.floatToIntBits(this.y) != Float.floatToIntBits(other.y)) {
            return false;
        }
        if (Float.floatToIntBits(this.z) != Float.floatToIntBits(other.z)) {
            return false;
        }
        if (Float.floatToIntBits(this.rx) != Float.floatToIntBits(other.rx)) {
            return false;
        }
        if (Float.floatToIntBits(this.ry) != Float.floatToIntBits(other.ry)) {
            return false;
        }
        if (Float.floatToIntBits(this.rz) != Float.floatToIntBits(other.rz)) {
            return false;
        }
        if (!world.equals(other.world)) {
            return false;
        }
        return true;
    }
}
