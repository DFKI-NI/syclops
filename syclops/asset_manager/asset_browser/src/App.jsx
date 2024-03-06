import React from "react";
import {
  Typography,
  CssBaseline,
  Toolbar,
  AppBar,
  Container,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  CardMedia,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  Button,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  Chip,
  OutlinedInput,
  Box,
  MenuItem,
  createTheme,
  ThemeProvider,
  Divider,
} from "@mui/material";

import catalog from "./catalog.json";
import ContentPasteIcon from "@mui/icons-material/ContentPaste";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";

import Carousel from "react-material-ui-carousel";

const theme = createTheme({
  palette: {
    primary: {
      main: "#9FC131",
    },
  },
});

const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
      width: 250,
    },
  },
};

const App = () => {
  const [open, setOpen] = React.useState(false);
  const [selected, setSelected] = React.useState(null);
  const [searchTerm, setSearchTerm] = React.useState("");
  const [selectedLibrary, setSelectedLibrary] = React.useState([]);
  const [selectedType, setSelectedType] = React.useState([]);

  const handleClickOpen = (library, asset) => {
    setOpen(true);
    setSelected({ library, asset });
  };

  const handleClose = () => {
    setOpen(false);
  };
  const handleClipboard = () => {
    // Add asset and library to clipboard
    const { library, asset } = selected;
    const text = `${library}/${asset}`;
    navigator.clipboard.writeText(text);
  };

  const handleLibSelect = (event) => {
    const {
      target: { value },
    } = event;
    setSelectedLibrary(
      // On autofill we get a stringified value.
      typeof value === "string" ? value.split(",") : value
    );
  };
  const handleTypeSelect = (event) => {
    const {
      target: { value },
    } = event;
    setSelectedType(
      // On autofill we get a stringified value.
      typeof value === "string" ? value.split(",") : value
    );
  };

  const findAllTypes = () => {
    const types = [];
    Object.keys(catalog).map((library) => {
      Object.keys(catalog[library]["assets"]).map((asset) => {
        if (!types.includes(catalog[library]["assets"][asset]["type"])) {
          types.push(catalog[library]["assets"][asset]["type"]);
        }
      });
    });
    return types;
  };

  return (
    <>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AppBar position="relative">
          <Toolbar>
            <Typography color="common.white" variant="h6">
              Asset Browser
            </Typography>
          </Toolbar>
        </AppBar>
        <Container sx={{ padding: 2, paddingBottom: 0 }}>
          <TextField
            id="search-bar"
            label="Search"
            variant="outlined"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            fullWidth
          />
        </Container>
        <Container
          sx={{
            padding: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <FormControl sx={{ width: 200 }}>
            <InputLabel id="library-select-label">Library</InputLabel>
            <Select
              labelId="library-select-label"
              id="library-select"
              multiple
              value={selectedLibrary}
              onChange={handleLibSelect}
              input={
                <OutlinedInput id="select-multiple-chip" label="Library" />
              }
              renderValue={(selected) => (
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip key={value} label={value} />
                  ))}
                </Box>
              )}
              MenuProps={MenuProps}
            >
              {Object.keys(catalog).map((libraryName) => (
                <MenuItem key={libraryName} value={libraryName}>
                  {libraryName}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl sx={{ width: 200, marginLeft: 1 }}>
            <InputLabel id="type-select-label">Type</InputLabel>
            <Select
              labelId="type-select-label"
              id="type-select"
              multiple
              value={selectedType}
              onChange={handleTypeSelect}
              input={<OutlinedInput id="select-multiple-chip" label="Type" />}
              renderValue={(selected) => (
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip key={value} label={value} />
                  ))}
                </Box>
              )}
              MenuProps={MenuProps}
            >
              {findAllTypes().map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {/* Button with full height inside container */}
          <Button
            variant="outlined"
            startIcon={<DeleteIcon />}
            onClick={() => {
              setSelectedLibrary([]);
              setSelectedType([]);
              setSearchTerm("");
            }}
            sx={{
              marginLeft: 1,
            }}
          >
            Clear
          </Button>
        </Container>
        <Divider variant="middle" />

        <main>
          <Container sx={{ padding: 2 }}>
            <Grid container spacing={3}>
              {Object.keys(catalog)
                .sort()
                .map((key) => {
                  const assets = catalog[key]["assets"];
                  return Object.keys(assets)
                    .sort()
                    .filter((asset) => {
                      // Filter out assets that don't match the search term
                      // Check Name, Type, Tags and Library
                      return (
                        (asset
                          .toLowerCase()
                          .includes(searchTerm.toLowerCase()) ||
                          assets[asset]["type"]
                            .toLowerCase()
                            .includes(searchTerm.toLowerCase()) ||
                          assets[asset]["tags"].some((tag) =>
                            tag.toLowerCase().includes(searchTerm.toLowerCase())
                          ) ||
                          key
                            .toLowerCase()
                            .includes(searchTerm.toLowerCase())) &&
                        (selectedLibrary.includes(key) ||
                          selectedLibrary.length === 0) &&
                        (selectedType.includes(assets[asset]["type"]) ||
                          selectedType.length === 0)
                      );
                    })
                    .map((assetKey) => {
                      const asset = assets[assetKey];
                      if (
                        asset.type === "model" ||
                        asset.type === "pbr_texture" ||
                        asset.type === "output" ||
                        asset.type === "plugin" ||
                        asset.type === "environment_texture" ||
                        asset.type === "sensor"
                      ) {
                        switch (asset.type) {
                          case "plugin":
                            var thumbnail_path = "icons/plugin.png";
                            break;
                          case "sensor":
                            var thumbnail_path = "icons/sensor.png";
                            break;
                          case "output":
                            var thumbnail_path = "icons/output.png";
                            break;
                          default:
                            try {
                              var thumbnail_path = asset.thumbnail[0].replace(
                                "\\",
                                "/"
                              );
                              // Split path and filename
                              var path = thumbnail_path.split("/");
                              var filename = path.pop();
                              path.push(key + "_" + filename);
                              // Join path back together
                              thumbnail_path = path.join("/");
                              break;
                            }
                            catch (error) {
                              var thumbnail_path = "icons/missing.png";
                              console.log(error);
                              console.log(asset);
                              break;
                            }
                        }
                        return (
                          <Grid item xs={12} sm={6} md={3} key={key + assetKey}>
                            <Card
                              sx={{ maxWidth: 345 }}
                              onClick={() => handleClickOpen(key, assetKey)}
                            >
                              <CardActionArea>
                                <CardMedia
                                  component="img"
                                  height="250"
                                  // asset.thumbnail first element
                                  image={require(`./${thumbnail_path}`)}
                                  alt="asset"
                                />
                                <CardContent>
                                  <Typography
                                    gutterBottom
                                    variant="h5"
                                    component="div"
                                  >
                                    {assetKey}
                                  </Typography>
                                  <Typography
                                    variant="body2"
                                    color="text.secondary"
                                  >
                                    {key}
                                  </Typography>
                                </CardContent>
                              </CardActionArea>
                            </Card>
                          </Grid>
                        );
                      } else {
                        return null;
                      }
                    });
                })}
            </Grid>
          </Container>
          {selected && (
            <>
              <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
                <DialogContent sx={{ padding: 0 }}>
                  <Carousel autoPlay={false} fullHeightHover={true}>
                    {catalog[selected.library]["assets"][selected.asset][
                      "thumbnail"
                    ].map((image) => {
                      var thumbnail_path = image.replace("\\", "/");
                      // Split path and filename
                      var path = thumbnail_path.split("/");
                      var filename = path.pop();
                      // Add "Test_" infront of filename
                      path.push(selected.library + "_" + filename);
                      // Join path back together
                      thumbnail_path = path.join("/");

                      return (
                        <img
                          src={require(`./${thumbnail_path}`)}
                          alt="asset"
                          style={{ maxWidth: "100%", width: "100%" }}
                        />
                      );
                    })}
                  </Carousel>
                  <DialogContentText sx={{ padding: 3 }}>
                    <Typography variant="h4">{selected.asset}</Typography>
                    <Typography variant="h6">{selected.library}</Typography>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        width: "fit-content",
                        "& svg": {
                          m: 1.5,
                        },
                        "& hr": {
                          mx: 0.5,
                        },
                      }}
                    >
                      {catalog[selected.library]["assets"][selected.asset][
                        "license"
                      ] && (
                        <>
                          <Typography display="inline">
                            License:{" "}
                            {
                              catalog[selected.library]["assets"][
                                selected.asset
                              ]["license"]
                            }
                          </Typography>
                        </>
                      )}
                      {catalog[selected.library]["assets"][selected.asset][
                        "vertices"
                      ] && (
                        <>
                          <Divider orientation="vertical" flexItem />
                          <Typography display="inline">
                            Vertices:{" "}
                            {
                              catalog[selected.library]["assets"][
                                selected.asset
                              ]["vertices"]
                            }
                          </Typography>
                        </>
                      )}
                      {catalog[selected.library]["assets"][selected.asset][
                        "height"
                      ] && (
                        <>
                          <Divider orientation="vertical" flexItem />
                          <Typography display="inline">
                            Height:{" "}
                            {catalog[selected.library]["assets"][
                              selected.asset
                            ]["height"].toFixed(2)}
                            {"m"}
                          </Typography>
                        </>
                      )}
                    </Box>
                  </DialogContentText>
                </DialogContent>
                <DialogActions>
                  <Button onClick={handleClipboard}>
                    Copy
                    <ContentPasteIcon />
                  </Button>
                  <Button onClick={handleClose} autoFocus>
                    Close
                    <CloseIcon />
                  </Button>
                </DialogActions>
              </Dialog>
            </>
          )}
        </main>
      </ThemeProvider>
    </>
  );
};

export default App;