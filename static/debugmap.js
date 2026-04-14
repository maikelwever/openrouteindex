onload = (event) => {
    const mapL = new maplibregl.Map({
        container: 'map',
        style: 'https://tiles.openfreemap.org/styles/positron',
        center: [5.5, 52],
        zoom: 7
    });

    mapL.on("load", async function() {
        const debugFile = document.location.hash.split("#")[1];
        if (debugFile.length === 0) return;

        const response = await fetch(debugFile);
        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }

        const result = await response.json();
        mapL.addSource('route', {
            'type': 'geojson',
            'data': result
        });
        mapL.addLayer({
            'id': 'route',
            'type': 'line',
            'source': 'route',
            'layout': {
                'line-join': 'round',
                'line-cap': 'round'
            },
            'paint': {
                'line-width': 3,
                'line-color': ['coalesce',
                    ['get', 'stroke'],
                    'green'
                ]
            },
        });
        const coordinates = result.features[0].geometry.coordinates[0];
        const bounds = result.features.reduce((bounds, feature) => {
            return bounds.extend(feature.geometry.coordinates.reduce((ibounds, coords) => {
                return ibounds.extend(coords);
            }, bounds));
        }, new maplibregl.LngLatBounds(coordinates, coordinates));

        mapL.fitBounds(bounds, {
            padding: 200
        });
    });
}
