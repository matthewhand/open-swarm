export async function fetchBlueprints() {
    try {
        const response = await fetch('/v1/models/');
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const data = await response.json();
        console.log('Raw blueprint data:', data);
        return data.data.filter(model => model.object === 'model');
    } catch (error) {
        console.error('Error fetching blueprints:', error);
        return [];
    }
}
